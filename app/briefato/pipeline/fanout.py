"""Fan-out — bounded-parallel per-segment compression + one final weave.

OWNER: WORKSTREAM-ENGINE-V2.

The fan-out pipeline Mohamed asked for: every source segment is summarised **on its own**
(with the kern/stolperfallen compression rules) by a **bounded concurrent executor (hard
cap, default 3 in flight)**, and the compressed segments are then rewritten into the final
document by exactly **one weave call**. The existing rule checker (with its one retry) runs
on the weave output.

Partial failures are never silent: a segment that fails is retried once; if it still fails
the letter is generated **without** it and the fact is reported as a gap (``gap=True`` on
the result, listed in the runtime detail and the audit) — never invented, never dropped
silently.

Concurrency guarantee: the executor's worker pool is sized to the cap and an explicit
semaphore-based tracker raises if the number of genuinely in-flight calls would ever exceed
it, so ``max_parallel`` can never be violated even if a future edit bypasses the pool.
"""

from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from ..brain.prompt_assembly import build_weave_prompt, correction_block
from ..brain.rule_checker import autofix_umlauts, check as rule_check

DEFAULT_MAX_PARALLEL = 3
#: Sanity ceiling so a mis-set environment variable cannot melt the provider.
HARD_MAX_PARALLEL = 8


def resolve_max_parallel(explicit: int | None = None) -> int:
    """Resolve the concurrency cap (``BRIEFATO_MAX_PARALLEL``, default 3, clamped 1..8)."""
    if explicit is None:
        raw = os.environ.get("BRIEFATO_MAX_PARALLEL", "").strip()
        try:
            explicit = int(raw) if raw else DEFAULT_MAX_PARALLEL
        except ValueError:
            explicit = DEFAULT_MAX_PARALLEL
    return max(1, min(int(explicit), HARD_MAX_PARALLEL))


class ConcurrencyTracker:
    """Counts provider calls and guards the in-flight concurrency cap."""

    def __init__(self, cap: int) -> None:
        self.cap = max(1, int(cap))
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._in_flight = 0
        self.peak = 0
        self.calls = 0

    def enter(self) -> None:
        with self._condition:
            if self._in_flight >= self.cap:
                self._condition.wait_for(lambda: self._in_flight < self.cap)
            self._in_flight += 1
            if self._in_flight > self.cap:  # pragma: no cover - belt & braces
                raise RuntimeError("fan-out concurrency cap exceeded")
            self.peak = max(self.peak, self._in_flight)

    def exit(self) -> None:
        with self._condition:
            self._in_flight = max(0, self._in_flight - 1)
            self._condition.notify()

    def record_call(self) -> None:
        with self._lock:
            self.calls += 1

    @property
    def in_flight(self) -> int:
        with self._lock:
            return self._in_flight


class TrackedProvider:
    """Transparent provider wrapper that counts calls and peaks across threads."""

    def __init__(self, inner: Any, tracker: ConcurrencyTracker) -> None:
        self._inner = inner
        self._tracker = tracker

    def __getattr__(self, name: str) -> Any:  # delegate name/provider attributes
        return getattr(self._inner, name)

    def generate(self, system: str, user: str, *, max_tokens: int = 2000, temperature: float = 0.2):
        self._tracker.record_call()
        return self._inner.generate(system, user, max_tokens=max_tokens, temperature=temperature)


@dataclass(frozen=True)
class CompressedSegment:
    """The result of compressing one source segment."""

    segment_type: str
    text: str
    ok: bool
    attempts: int
    confidence: float
    index: int
    error: str = ""

    @property
    def gap(self) -> bool:
        return not self.ok

    def as_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "type": self.segment_type,
            "ok": self.ok,
            "attempts": self.attempts,
            "confidence": round(self.confidence, 3),
            "chars": len(self.text or ""),
            "error": self.error,
        }


def compress_segments(
    segments: Sequence[Any],
    *,
    provider: Any,
    doc_type: str,
    tracker: ConcurrencyTracker,
    max_parallel: int | None = None,
    guard: Callable[[str, str], None] | None = None,
    enrichment: list | None = None,
    language: str = "de",
) -> tuple[list[CompressedSegment], dict[str, Any]]:
    """Compress every segment concurrently (hard cap) and return results + stats.

    Each segment is attempted once and, on any error, retried exactly once. A segment that
    still fails becomes a gap (``ok=False``) with its error recorded — the caller keeps the
    letter but reports the gap.
    """
    from ..brain.prompt_assembly import build_compression_prompt

    cap = resolve_max_parallel(max_parallel)
    jobs = list(segments or [])

    def _one(segment: Any) -> CompressedSegment:
        index = int(getattr(segment, "index", 0) or 0)
        segment_type = str(getattr(segment, "segment_type", "rohtext") or "rohtext")
        text = str(getattr(segment, "text", "") or "")
        confidence = float(getattr(segment, "confidence", 0.0) or 0.0)
        attempts = 0
        error = ""
        for _attempt in range(2):  # once + one retry
            attempts += 1
            try:
                bundle = build_compression_prompt(
                    doc_type=doc_type,
                    segment_type=segment_type,
                    segment_text=text,
                    language=language,
                    enrichment=enrichment,
                )
                if guard is not None:
                    guard(bundle.system, bundle.user)
                with _Slot(tracker):
                    result = provider.generate(bundle.system, bundle.user)
                # Normalise whitespace but keep line breaks (a compressed Diagnosen /
                # Therapieempfehlungen block is a list — one entry per line).
                raw_text = getattr(result, "text", "") or ""
                compressed = "\n".join(
                    " ".join(line.split()) for line in raw_text.splitlines() if line.strip()
                )
                # An empty compression is legitimate (a source with no distilled insight,
                # e.g. pure nursing routine) — it is not a failure. Only an exception is.
                return CompressedSegment(segment_type, compressed, True, attempts, confidence, index, "")
            except Exception as exc:  # noqa: BLE001 - retry then record the gap
                error = f"{type(exc).__name__}"
        return CompressedSegment(segment_type, "", False, attempts, confidence, index, error)

    results: list[CompressedSegment | None] = [None] * len(jobs)
    if jobs:
        workers = min(cap, len(jobs)) or 1
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="briefato-fanout") as executor:
            futures = {executor.submit(_one, segment): position for position, segment in enumerate(jobs)}
            for future, position in futures.items():
                results[position] = future.result()

    ordered = [item for item in results if item is not None]
    gaps = [item for item in ordered if item.gap]
    stats = {
        "max_parallel": cap,
        "segments_total": len(jobs),
        "segments_ok": sum(1 for item in ordered if item.ok),
        "segments_failed": len(gaps),
        "gaps": [item.as_dict() for item in gaps],
        # Per-segment compression result (bounded text) for the UI/audit/demo.
        "results": [
            {**item.as_dict(), "text": (item.text or "")[:400]} for item in ordered
        ],
        "compression_calls": sum(item.attempts for item in ordered),
        "peak_concurrency": tracker.peak,
    }
    return ordered, stats


class _Slot:
    """Context manager acquiring one concurrency slot (never exceeding the cap)."""

    def __init__(self, tracker: ConcurrencyTracker) -> None:
        self._tracker = tracker

    def __enter__(self) -> "_Slot":
        self._tracker.enter()
        return self

    def __exit__(self, *_exc) -> bool:
        self._tracker.exit()
        return False


def run_weave(
    *,
    doc_type: str,
    compressed: Sequence[CompressedSegment],
    provider: Any,
    pseudonymizer: Any,
    letterhead: dict,
    patient_ctx: dict,
    templates: list | None,
    custom_rules: str,
    enrichment: list | None,
    extra: str = "",
    guard: Callable[[str, str], None] | None = None,
    dictation: str = "",
    language: str = "de",
) -> dict[str, Any]:
    """One weave call (plus at most one rule-check retry) producing the final document."""
    ok_segments = [item for item in compressed if item.ok and item.text]

    def _call(prompt_extra: str):
        bundle = build_weave_prompt(
            doc_type=doc_type,
            compressed=ok_segments,
            letterhead=letterhead,
            patient_ctx=patient_ctx,
            templates=list(templates or []),
            custom_rules=custom_rules,
            enrichment=enrichment,
            extra=prompt_extra,
            language=language,
        )
        if guard is not None:
            guard(bundle.system, bundle.user)
        result = provider.generate(bundle.system, bundle.user)
        restored = pseudonymizer.restore(result.text)
        fixed, umlaut_fixes = autofix_umlauts(restored)
        from ..brain.prompt_assembly import reference_support_text  # local: avoid import cycle

        reference = reference_support_text(templates, enrichment)
        return bundle, result, fixed, rule_check(
            fixed, doc_type, dictation, autofix=umlaut_fixes, reference=reference
        )

    bundle, result, text, check_result = _call(extra or "")
    retried = False
    if check_result.hard:
        retried = True
        correction = correction_block(check_result.correction_instructions())
        retry_extra = ((extra or "") + "\n\n" + correction).strip()
        try:
            bundle2, result2, text2, check2 = _call(retry_extra)
        except Exception:  # pragma: no cover - keep the first draft if the retry dies
            pass
        else:
            if len(check2.hard) <= len(check_result.hard):
                bundle, result, text, check_result = bundle2, result2, text2, check2

    return {
        "doc_type": doc_type,
        "text": text,
        "result": result,
        "bundle": bundle,
        "check": check_result,
        "retried": retried,
        "weave_calls": 2 if retried else 1,
    }


__all__ = [
    "CompressedSegment",
    "ConcurrencyTracker",
    "DEFAULT_MAX_PARALLEL",
    "TrackedProvider",
    "compress_segments",
    "resolve_max_parallel",
    "run_weave",
]

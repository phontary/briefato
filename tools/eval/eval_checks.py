"""Deterministic expectation checks: must_contain / must_not_contain / structure.

These are the *human-written quality expectations* of a corpus case, evaluated
mechanically against the model output. They complement the R1–R67 rule checker
(the source of truth for method compliance, imported read-only elsewhere).

Matching rules
--------------
Text is umlaut-folded (ä→ae …) and lowercased, then all runs of non-alphanumeric
characters are collapsed to single spaces on **both** sides. An expectation item
matches when its canon form appears as a whole word/phrase in the canon output
(``(?<![a-z0-9])`` … ``(?![a-z0-9])``), so ``Dg.:`` does **not** match inside
``Handgelenk``. Items that consist only of punctuation (e.g. ``**``) fall back to a
raw substring test.

Pure stdlib. No repo imports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_UMLAUT_MAP = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
_NON_ALNUM = re.compile(r"[^a-z0-9]+")

# Canonical terminal block order per document type (mirrors rule_checker R25/R27,
# used as an independent structural check on the *output*).
CANONICAL_BLOCK_ORDER: dict[str, tuple[str, ...]] = {
    "arztbrief": (
        "ambulante Therapieempfehlungen nach der Entlassung:",
        "Diagnosen:",
        "Nebenerkrankungen:",
        "Therapie-Maßnahmen auf der Station:",
    ),
    "operationsbericht": (
        "Indikation:",
        "OP:",
        "Präparat:",
        "Diagnosen:",
        "Operation:",
    ),
    "ambulant": ("Diagnosen:",),
    "zusammenfassung": (),
}


def fold(text: str) -> str:
    text = (text or "").lower()
    for source, target in _UMLAUT_MAP.items():
        text = text.replace(source, target)
    return text


def canon(text: str) -> str:
    """Umlaut-folded, lowercased, punctuation collapsed to single spaces."""
    return " ".join(_NON_ALNUM.sub(" ", fold(text)).split())


def canon_colon(text: str) -> str:
    """Like :func:`canon` but keeps a trailing/embedded colon, so label items stay precise.

    ``"Therapie-Maßnahmen auf der Station:"`` → ``"therapie massnahmen auf der station:"``.
    """
    folded = fold(text)
    return " ".join(re.sub(r"[^a-z0-9:]+", " ", folded).split())


def _item_pattern(item: str) -> re.Pattern[str] | None:
    folded = _NON_ALNUM.sub(" ", fold(item)).strip()
    if not folded:
        return None  # punctuation-only item → raw substring fallback
    body = r"\s+".join(re.escape(part) for part in folded.split())
    return re.compile(r"(?<![a-z0-9])" + body + r"(?![a-z0-9])")


def _contains_label(output: str, stripped: str) -> bool:
    needle = canon_colon(stripped)
    if not needle:
        return stripped in (output or "")
    haystack = canon_colon(output)
    start = 0
    while True:
        found = haystack.find(needle, start)
        if found == -1:
            return False
        if found == 0 or haystack[found - 1] == " ":
            return True
        start = found + 1


def contains(output: str, item: str) -> bool:
    """Relaxed match for ``must_contain`` / block presence.

    Colon-terminated items are treated as *labels* and require the colon
    (``"CT:"`` does not match the plain word ``CT``). All other items match as a
    case/umlaut-folded **substring**, so German inflection and compounding work:
    ``"Rektumkarzinom"`` matches ``Rektumkarzinoms`` and ``"Divertikulitis"`` matches
    ``Sigmadivertikulitis``.
    """
    stripped = (item or "").strip()
    if stripped.endswith(":"):
        return _contains_label(output, stripped)
    needle = canon(stripped)
    if not needle:
        return stripped in (output or "")
    return needle in canon(output)


def contains_strict(output: str, item: str) -> bool:
    """Strict whole-word match for ``must_not_contain`` (no false positives).

    ``"Dg.:"`` matches only a real ``Dg.:`` label, never the ``dg`` inside
    ``Handgelenk``; ``"Troponin"`` never matches ``Troponinkontrolle``.
    """
    stripped = (item or "").strip()
    if stripped.endswith(":"):
        return _contains_label(output, stripped)
    pattern = _item_pattern(item)
    if pattern is None:
        return stripped in (output or "")
    return bool(pattern.search(canon(output)))


@dataclass
class ContainmentResult:
    matched: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.matched) + len(self.missing)

    @property
    def coverage(self) -> float:
        return len(self.matched) / self.total if self.total else 1.0

    def as_dict(self) -> dict[str, object]:
        return {
            "matched": self.matched,
            "missing": self.missing,
            "total": self.total,
            "coverage": round(self.coverage, 4),
        }


def check_must_contain(output: str, items: list[str]) -> ContainmentResult:
    matched = [item for item in items if contains(output, item)]
    missing = [item for item in items if item not in matched]
    return ContainmentResult(matched=matched, missing=missing)


def check_must_not_contain(output: str, items: list[str]) -> list[str]:
    """Return the forbidden items that DID appear (violations) — strict whole-word match."""
    return [item for item in items if contains_strict(output, item)]


@dataclass
class StructureResult:
    present: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    order_ok: bool = True
    canonical_missing: list[str] = field(default_factory=list)
    canonical_order_ok: bool = True

    @property
    def ok(self) -> bool:
        return not self.missing and self.order_ok and self.canonical_order_ok

    def as_dict(self) -> dict[str, object]:
        return {
            "present": self.present,
            "missing": self.missing,
            "order_ok": self.order_ok,
            "canonical_missing": self.canonical_missing,
            "canonical_order_ok": self.canonical_order_ok,
            "ok": self.ok,
        }


def _block_line_index(output: str, block: str) -> int | None:
    """Line index of a block label (exact line, then line-prefix, then anywhere)."""
    target = canon(block)
    if not target:
        return None
    lines = output.splitlines()
    for index, line in enumerate(lines):
        if canon(line) == target:
            return index
    for index, line in enumerate(lines):
        line_canon = canon(line)
        if line_canon.startswith(target + " ") or line_canon.startswith(target):
            return index
    # fallback: locate in the folded full text by character offset (ordered)
    folded = canon(output)
    pos = folded.find(" " + target + " ")
    if pos == -1 and folded.startswith(target + " "):
        pos = 0
    return pos if pos != -1 else None


def _order_ok(output: str, blocks: list[str]) -> tuple[bool, list[str]]:
    indices: list[int] = []
    located: list[str] = []
    for block in blocks:
        index = _block_line_index(output, block)
        if index is None:
            continue
        indices.append(index)
        located.append(block)
    if len(indices) < 2:
        return True, located
    return indices == sorted(indices), located


def check_structure(
    output: str,
    doc_type: str,
    expected_blocks: list[str],
) -> StructureResult:
    present = [block for block in expected_blocks if contains(output, block)]
    missing = [block for block in expected_blocks if block not in present]
    order_ok, _ = _order_ok(output, present)

    canonical = list(CANONICAL_BLOCK_ORDER.get(doc_type, ()))
    canonical_present = [block for block in canonical if contains(output, block)]
    canonical_missing = [block for block in canonical if block not in canonical_present]
    canonical_order_ok, _ = _order_ok(output, canonical_present)

    return StructureResult(
        present=present,
        missing=missing,
        order_ok=order_ok,
        canonical_missing=canonical_missing,
        canonical_order_ok=canonical_order_ok,
    )


__all__ = [
    "CANONICAL_BLOCK_ORDER",
    "ContainmentResult",
    "StructureResult",
    "canon",
    "canon_colon",
    "check_must_contain",
    "check_must_not_contain",
    "check_structure",
    "contains",
    "contains_strict",
    "fold",
]

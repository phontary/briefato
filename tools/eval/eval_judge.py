"""Optional LLM-judge rubric (0–5) for the Briefato quality harness.

Only used when ``--judge-model`` is configured. The judge is an independent,
OpenAI-compatible chat model (usually a *different* model than the one under test)
that scores the finished document on the five axes that the deterministic checks
cannot fully capture:

1. structure & order          (Playbook-Reihenfolge, Blocklogik)
2. completeness               (kein diktierter Fakt verloren)
3. no-invention               (kein Fakt, der nicht in den Quellen steht)
4. register & abbreviations   (sachlich-fachlich, Abkürzungen direkt)
5. plain-text compliance      (kein Markdown, kein Label-Rauschen, Umlaute)

Each axis returns a 0–5 score, a one-line reason and — when a rule is violated — a
citation of the offending passage (``citation``).

The judge is fed the *dictation* (as the only admissible source of facts) and the
finished *output*, never the patient record. It is explicitly instructed that the
dictation is the ground truth for "no invention".

No network import happens at module load; the provider is injected. This module is
never exercised in the offline/mock test run.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

AXES: tuple[str, ...] = (
    "structure",
    "completeness",
    "no_invention",
    "register",
    "plain_text",
)

AXIS_LABELS: dict[str, str] = {
    "structure": "Struktur & Reihenfolge",
    "completeness": "Vollständigkeit (kein diktierter Fakt verloren)",
    "no_invention": "Keine Erfindung (kein Fakt außerhalb der Quellen)",
    "register": "Register & Abkürzungen",
    "plain_text": "Plain-Text-Konformität",
}

_JUDGE_SYSTEM = (
    "Sie sind ein strenger, unabhängiger Gutachter für deutschsprachige medizinische "
    "Arztbriefe. Sie bewerten ausschließlich den gelieferten Text anhand des Diktats "
    "als einziger Faktenquelle. Sie erfinden nichts und loben nicht pauschal. "
    "Antworten Sie ausschließlich mit gültigem JSON, ohne Markdown."
)


def build_judge_prompt(dictation: str, output: str, doc_type: str) -> tuple[str, str]:
    """Return ``(system, user)`` for the judge call."""
    user = (
        f"Dokumenttyp: {doc_type}\n\n"
        "DIKTAT (einzige zulässige Faktenquelle):\n"
        "-----\n"
        f"{dictation}\n"
        "-----\n\n"
        "ZU BEWERTENDER TEXT:\n"
        "-----\n"
        f"{output}\n"
        "-----\n\n"
        "Bewerten Sie JEDE der fünf Achsen mit einer ganzen Zahl von 0 (unbrauchbar) "
        "bis 5 (einwandfrei). Geben Sie je Achse eine einzeilige Begründung (reason) und, "
        "falls eine Regel verletzt ist, die beanstandete Textstelle wörtlich als citation "
        "(sonst leerer String).\n\n"
        "Achsen:\n"
        "- structure: Playbook-Reihenfolge und Blocklogik (Anamnese → Untersuchung → "
        "Diagnose → Therapie → Verlauf; Blöcke am Ende).\n"
        "- completeness: jeder im Diktat genannte klinisch relevante Fakt ist enthalten.\n"
        "- no_invention: kein Fakt (Diagnose, ICD, Datum, Laborwert, Medikament, "
        "Konsil) erscheint, der nicht im Diktat steht.\n"
        "- register: sachlicher fachlicher Stil, Abkürzungen direkt verwendet, "
        "keine Füllwörter, keine Kategorie-Labels im Fließtext.\n"
        "- plain_text: reiner Text, kein Markdown, korrekte Umlaute, höchstens ein Semikolon.\n\n"
        "Antwortformat (NUR dieses JSON, keine Erklärungen außerhalb):\n"
        '{"structure": {"score": 0-5, "reason": "...", "citation": ""}, '
        '"completeness": {...}, "no_invention": {...}, "register": {...}, '
        '"plain_text": {...}, "overall_comment": "..."}'
    )
    return _JUDGE_SYSTEM, user


@dataclass
class JudgeResult:
    scores: dict[str, int] = field(default_factory=dict)
    reasons: dict[str, str] = field(default_factory=dict)
    citations: dict[str, str] = field(default_factory=dict)
    overall_comment: str = ""
    mean: float | None = None
    error: str = ""
    model: str = ""

    @property
    def ok(self) -> bool:
        return not self.error and bool(self.scores)

    def as_dict(self) -> dict[str, object]:
        return {
            "model": self.model,
            "scores": self.scores,
            "reasons": self.reasons,
            "citations": self.citations,
            "mean": round(self.mean, 2) if self.mean is not None else None,
            "overall_comment": self.overall_comment,
            "error": self.error,
        }


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no JSON object in judge response")
    return json.loads(text[start : end + 1])


def parse_judge_response(text: str) -> JudgeResult:
    """Parse the judge's JSON into a :class:`JudgeResult` (lenient, clamped 0–5)."""
    data = _extract_json(text)
    scores: dict[str, int] = {}
    reasons: dict[str, str] = {}
    citations: dict[str, str] = {}
    for axis in AXES:
        entry = data.get(axis) or {}
        if isinstance(entry, dict):
            raw = entry.get("score")
            reason = str(entry.get("reason") or "")
            citation = str(entry.get("citation") or "")
        else:
            raw = entry
            reason = citation = ""
        try:
            score = int(round(float(raw)))
        except (TypeError, ValueError):
            continue
        scores[axis] = max(0, min(5, score))
        reasons[axis] = reason
        citations[axis] = citation
    mean = sum(scores.values()) / len(scores) if scores else None
    return JudgeResult(
        scores=scores,
        reasons=reasons,
        citations=citations,
        overall_comment=str(data.get("overall_comment") or ""),
        mean=mean,
    )


def judge_output(
    provider,
    *,
    dictation: str,
    output: str,
    doc_type: str,
    model: str = "",
) -> JudgeResult:
    """Call ``provider`` (an :class:`LLMProvider`) and parse the rubric scores.

    Any failure is captured in :attr:`JudgeResult.error` — a broken judge must never
    fail the whole evaluation run.
    """
    system, user = build_judge_prompt(dictation, output, doc_type)
    try:
        result = provider.generate(system, user, max_tokens=1200, temperature=0.0)
    except Exception as exc:  # noqa: BLE001 - judge failures are non-fatal by design
        return JudgeResult(error=f"{type(exc).__name__}: {exc}", model=model)
    try:
        parsed = parse_judge_response(result.text)
    except Exception as exc:  # noqa: BLE001
        return JudgeResult(error=f"parse: {type(exc).__name__}", model=model)
    parsed.model = model or getattr(result, "model", "")
    return parsed


__all__ = [
    "AXES",
    "AXIS_LABELS",
    "JudgeResult",
    "build_judge_prompt",
    "judge_output",
    "parse_judge_response",
]

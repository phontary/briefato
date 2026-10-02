"""Grounded enrichment ('Improvisation') — base contracts and the generic-knowledge guardrail.

OWNER: WORKSTREAM-ENGINE-V2.

Mohamed's decision (2026-10-02): improvising routine technique / standard materials /
typical follow-up for a standard operation whose dictation omits them is **indispensable**
— but it must be *grounded*. The method allows deriving those details from the Musterbrief
archive and researching new ones (AMBOSS/DocCheck/PubMed/AWMF) with a ``## Quellen`` record.
Free invention of patient-specific facts stays forbidden.

This module fixes the contract:

* an :class:`Enrichment` is a single generic statement plus its **source** (a URL or a
  Musterbrief filename);
* a :class:`ResearchProvider` produces enrichments for a document;
* :class:`NullEnricher` is the default (no research);
* :func:`is_generic_statement` is the guardrail enforced on **every** candidate — it blocks
  anything carrying a date, a dosing, an ICD code, a patient identifier from this request,
  a patient-possessive phrasing, or a verbatim span copied from the patient's dictation.

Enrichment may only add **generic, standard, non-patient-specific** knowledge (technique,
standard materials, typical follow-up intervals, standard medication classes). It must
never add a diagnosis, date, dosage, finding or name for this patient.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable

# --------------------------------------------------------------------------- settings


def research_base_url() -> str:
    """SearXNG base URL from ``BRIEFATO_RESEARCH_BASE_URL`` (empty = web research off)."""
    return os.environ.get("BRIEFATO_RESEARCH_BASE_URL", "").strip()


def enrich_default() -> bool:
    """Whether enrichment is opt-in-by-default (``BRIEFATO_ENRICH_DEFAULT``, default off)."""
    raw = os.environ.get("BRIEFATO_ENRICH_DEFAULT", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


# --------------------------------------------------------------------------- record


@dataclass(frozen=True)
class Enrichment:
    """One grounded, generic, non-patient-specific statement plus its source."""

    statement: str
    source: str
    kind: str = "standard"  # technique | materials | follow_up | medication_class | standard
    origin: str = "archive"  # archive | web
    score: float = 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "statement": self.statement,
            "source": self.source,
            "kind": self.kind,
            "origin": self.origin,
            "score": round(float(self.score), 4),
        }


@runtime_checkable
class ResearchProvider(Protocol):
    """A grounded enrichment backend."""

    def enrich(
        self,
        *,
        doc_type: str,
        context_text: str,
        patient_context: dict[str, str] | None = None,
        dictation: str = "",
        max_items: int = 6,
    ) -> list[Enrichment]: ...


class NullEnricher:
    """Default provider: perform no research at all."""

    origin = "null"

    def enrich(self, **_kwargs) -> list[Enrichment]:
        return []


# --------------------------------------------------------------------------- guardrail

_DATE_RE = re.compile(
    r"\b\d{1,2}\.\d{1,2}\.?\d{0,4}\b"
    r"|\b\d{4}-\d{2}-\d{2}\b"
    r"|\b(?:jan|feb|m(?:ä|ae)r|apr|mai|jun|jul|aug|sep|okt|nov|dez)[a-z]*\.?\s*\d{4}\b",
    re.IGNORECASE,
)
# A dosing: a number directly followed by a drug unit (or ¼ etc. glyphs).
_DOSAGE_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*"
    r"(?:mg|g|kg|ml|µg|ug|ng|pg|i\.?\s?e\.?|ie|meq|mmol|mol|%|einheiten|einheit|tropfen|hub)\b",
    re.IGNORECASE,
)
_ICD_RE = re.compile(r"(?<![A-Za-z0-9])[A-TV-Z]\d{2}(?:\.\d{1,2})?(?![0-9])")
_PATIENT_POSSESSIVE_RE = re.compile(
    r"\b(?:unser(?:e|er)?|dies(?:e|er|es)|bei (?:dies|unser)em?)\s+"
    r"(?:pat(?:ient(?:in)?)?|patienten|patientinnen|kind|herrn|frau)\b",
    re.IGNORECASE,
)
_VERBATIM_NGRAM = 7  # consecutive words shared with the patient's dictation -> reject

_MIN_STATEMENT_CHARS = 15
_MAX_STATEMENT_CHARS = 400


def _shares_word_ngram(a: str, b: str, n: int = _VERBATIM_NGRAM) -> bool:
    """True when ``a`` and ``b`` share a run of ``n`` consecutive words.

    A generic reference statement must not be copied out of (or into) the patient's
    dictation. Comparing word n-grams rather than character windows avoids the false
    positives a raw substring test produced against long dictations.
    """
    aw = re.findall(r"\w+", (a or "").lower())
    bw = re.findall(r"\w+", (b or "").lower())
    if len(aw) < n or len(bw) < n:
        return False
    grams = {" ".join(bw[i : i + n]) for i in range(len(bw) - n + 1)}
    for i in range(len(aw) - n + 1):
        if " ".join(aw[i : i + n]) in grams:
            return True
    return False


def is_generic_statement(
    statement: str,
    *,
    patient_context: dict[str, str] | None = None,
    dictation: str = "",
) -> bool:
    """Enforce the 'generic, non-patient-specific' rule on one candidate statement.

    Returns ``False`` (i.e. the statement must be dropped) when it carries:
    a date, a dosing with a unit, an ICD code, a patient identifier from this request,
    a patient-possessive phrasing, or a run of seven consecutive words copied from the
    patient's own dictation.
    """
    text = " ".join((statement or "").split())
    if len(text) < _MIN_STATEMENT_CHARS or len(text) > _MAX_STATEMENT_CHARS:
        return False

    lowered = text.lower()
    if _DATE_RE.search(text) or _DOSAGE_RE.search(text) or _ICD_RE.search(text):
        return False
    if _PATIENT_POSSESSIVE_RE.search(text):
        return False

    for value in (patient_context or {}).values():
        candidate = str(value or "").strip()
        if len(candidate) >= 3 and candidate.lower() in lowered:
            return False

    if dictation and _shares_word_ngram(text, dictation):
        return False
    return True


def filter_generic(
    enrichments: Sequence[Enrichment],
    *,
    patient_context: dict[str, str] | None = None,
    dictation: str = "",
) -> tuple[list[Enrichment], int]:
    """Return ``(kept, blocked_count)`` applying :func:`is_generic_statement`."""
    kept: list[Enrichment] = []
    blocked = 0
    seen: set[str] = set()
    for item in enrichments:
        key = " ".join((item.statement or "").lower().split())
        if not key or key in seen:
            continue
        if not is_generic_statement(item.statement, patient_context=patient_context, dictation=dictation):
            blocked += 1
            continue
        seen.add(key)
        kept.append(item)
    return kept, blocked


__all__ = [
    "Enrichment",
    "NullEnricher",
    "ResearchProvider",
    "enrich_default",
    "filter_generic",
    "is_generic_statement",
    "research_base_url",
]

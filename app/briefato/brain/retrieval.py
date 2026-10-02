"""Musterbrief retrieval — diagnose keyword matching against ``manifest.json``.

OWNER: WORKSTREAM-BRAIN-WIRING.

The retrieval scorer is a slightly extended version of the repository's own
``brain/musterbriefe/retrieval_selftest.py`` scorer (which hits 15/15 top-1 on the
self-test queries). Extensions:

* German lay synonyms / Oberbegriffe are expanded into clinical tokens
  ("Blinddarmentzündung" -> "Appendizitis", "Schaufensterkrankheit" -> "pAVK").
* Umlaut/ASCII normalisation (ä<->ae, ö<->oe, ü<->ue, ß<->ss) on both sides.
* filename stems participate as tokens (normalised filenames).

Two hard governance gates:

1. **Scrub-pending templates are never retrievable.** ``Cholezystolithiasis.md``,
   ``Acne-inversa.md`` and ``Struma_nodosa_Hyperthyreose.md`` carry patient traces
   (see ``brain/musterbriefe/scrub-report.md``); they are dropped before scoring.
2. **Licence-review templates are returned but flagged ``reference_only=True``.**
   Their *structure* may inspire the generated letter, but the licensed prose must
   never be shipped (see ``brain/musterbriefe/licence-review.md``).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Iterable

from . import brain_loader

# Templates that must never be retrieved (patient traces — scrub-report.md rule).
SCRUB_PENDING: frozenset[str] = frozenset(
    {
        "Cholezystolithiasis.md",
        "Acne-inversa.md",
        "Struma_nodosa_Hyperthyreose.md",
    }
)

# The 15 self-test queries from brain/musterbriefe/retrieval_selftest.py.
# (query, expected filename substring). Query 1's expected file is scrub-pending and
# is therefore intentionally excluded by this module — see README.
SELFTEST_QUERIES: tuple[tuple[str, str], ...] = (
    ("Gallensteine mit Kolik", "Cholezystolithiasis.md"),
    ("Subduralhämatom nach Sturz", "Subduralhaematom"),
    ("Divertikulitis linke Unterbauchschmerzen", "Divertikulitis"),
    ("Lungenembolie", "Lungenembolie.md"),
    ("AC-Gelenk Schulterverletzung", "AC-Gelenk"),
    ("Appendizitis Blinddarmentzündung", "append"),
    ("Leistenhernie Operation", "Leistenhernie"),
    ("Tiefe Beinvenenthrombose", "Tiefe_Beinvenenthrombose"),
    ("pAVK Schaufensterkrankheit", "pAVK"),
    ("Pneumonie Lungenentzündung", "Pneumonie.md"),
    ("Vorhofflimmern Herzrhythmusstörung", "Vorhofflimmern"),
    ("Nierensteine Kolik", "Urolithiasis"),
    ("Gichtanfall", "Gichtarthritis.md"),
    ("Schlaganfall Hemiparese", "Apoplex"),
    ("Harnwegsinfekt Blasenentzündung", "Harnwegsinfekt.md"),
)

# Lay term -> clinical tokens (Ober-/Teilbegriffe and common synonyms).
LAY_SYNONYMS: dict[str, tuple[str, ...]] = {
    "blinddarmentzuendung": ("appendizitis",),
    "blinddarmentzündung": ("appendizitis",),
    "blasenentzuendung": ("harnwegsinfekt",),
    "blasenentzündung": ("harnwegsinfekt",),
    "schaufensterkrankheit": ("pavk",),
    "lungenentzuendung": ("pneumonie",),
    "lungenentzündung": ("pneumonie",),
    "herzrhythmusstoerung": ("vorhofflimmern",),
    "herzrhythmusstörung": ("vorhofflimmern",),
    "nierensteine": ("urolithiasis", "nierenkolik"),
    "gallensteine": ("gallenblase", "cholezystitis", "cholezystolithiasis"),
    "gallenkolik": ("gallenblase", "cholezystitis"),
    "schlaganfall": ("apoplex",),
    "hirnschlag": ("apoplex",),
    "darmspiegelung": ("koloskopie",),
    "wasserlassen": ("miktion",),
    "uebelkeit": ("nausea",),
    "übelkeit": ("nausea",),
    "leistenbruch": ("leistenhernie",),
    "mandelentzuendung": ("tonsillitis",),
    "mandelentzündung": ("tonsillitis",),
    "knochenbruch": ("fraktur",),
    "gallenblasenentzuendung": ("cholezystitis",),
    "gallenblasenentzündung": ("cholezystitis",),
    "bauchspeicheldruesenentzuendung": ("pankreatitis",),
    "bauchspeicheldrüsenentzündung": ("pankreatitis",),
    "herzinfarkt": ("myokardinfarkt",),
    "lungenembolie": ("lungenembolie",),
    "thrombose": ("tiefe", "beinvenenthrombose"),
    "rheuma": ("arthritis",),
    "gicht": ("gichtarthritis",),
}

_STOP = {
    "mit", "und", "der", "die", "das", "bei", "nach", "von", "im", "in", "am",
    "auf", "den", "dem", "des", "eine", "einer", "einem", "ohne", "zur", "zum",
    "für", "fuer", "als", "ist", "ein", "vom", "aus", "den", "deren",
}

_REFERENCE_ONLY = "review"


def normalise(text: str) -> str:
    """Lowercase, transliterate umlauts, strip accents/punctuation, collapse spaces."""
    text = (text or "").lower()
    for source, target in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(source, target)
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _tokens(text: str, *, min_len: int = 3) -> set[str]:
    return {word for word in normalise(text).split() if len(word) >= min_len}


def _expand(query_tokens: list[str]) -> list[str]:
    """Append clinical synonyms for every lay term in the query (deduped)."""
    expanded = list(query_tokens)
    seen = set(query_tokens)
    for token in query_tokens:
        for synonym in LAY_SYNONYMS.get(token, ()):
            for extra in normalise(synonym).split():
                if len(extra) >= 3 and extra not in seen:
                    seen.add(extra)
                    expanded.append(extra)
    return expanded


@dataclass
class TemplateHit:
    """One retrieved Musterbrief."""

    file: str
    title: str
    group: str
    score: float
    sections_present: list[str] = field(default_factory=list)
    sections_missing: list[str] = field(default_factory=list)
    reference_only: bool = False
    scrub_pending: bool = False
    path: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "title": self.title,
            "score": self.score,
            "group": self.group,
            "reference_only": self.reference_only,
            "scrub_pending": self.scrub_pending,
            "sections_present": list(self.sections_present),
        }


@lru_cache(maxsize=1)
def available_templates() -> tuple[dict[str, Any], ...]:
    """Manifest entries that are allowed to be retrieved (scrub-pending removed).

    Each entry gains a private ``_toks`` token set used by the scorer.
    """
    kept: list[dict[str, Any]] = []
    for entry in brain_loader.templates():
        if entry.get("file") in SCRUB_PENDING:
            continue
        scored = dict(entry)
        tokens: set[str] = set()
        tokens |= _tokens(entry.get("title", ""))
        for keyword in entry.get("indication_keywords", []):
            tokens |= _tokens(keyword)
        stem = str(entry.get("file", ""))[:-3] if str(entry.get("file", "")).endswith(".md") else str(entry.get("file", ""))
        tokens |= _tokens(stem)
        scored["_toks"] = tokens
        kept.append(scored)
    return tuple(kept)


def _score(query_tokens: Iterable[str], candidate: dict[str, Any]) -> float:
    """Selftest-compatible scorer: exact match 2.0, substring overlap up to 1.4.

    The selftest divides by ``len(query)`` (a per-query constant), so dropping that
    division leaves the ranking unchanged while making long free-text dictations
    usable: templates that match many clinical concepts rank above noise.
    """
    query = [token for token in query_tokens if token not in _STOP]
    if not query:
        return 0.0
    cand = candidate["_toks"]
    total = 0.0
    matched = 0
    for q in query:
        best = 0.0
        for c in cand:
            if q == c:
                best = max(best, 2.0)
            elif len(q) >= 4 and (q in c or c in q):
                overlap = min(len(q), len(c))
                best = max(best, 1.0 + min(overlap, 8) / 20.0)
        if best > 0:
            matched += 1
        total += best
    coverage = matched / len(query)
    return round(total * (0.5 + 0.5 * coverage), 4)


def retrieve(
    query: str,
    *,
    limit: int = 5,
    min_score: float = 0.0,
    include_reference_only: bool = True,
) -> list[TemplateHit]:
    """Return the top-``limit`` Musterbriefe for ``query`` (best score first).

    Scrub-pending templates are excluded unconditionally. Licence-review templates
    are returned with ``reference_only=True`` unless ``include_reference_only=False``.
    """
    base = [word for word in normalise(query).split() if len(word) >= 3]
    expanded = _expand(base)
    ranked: list[TemplateHit] = []
    for entry in available_templates():
        score = _score(expanded, entry)
        if score <= 0 or score < min_score:
            continue
        reference_only = str(entry.get("licence_risk", "low")).lower() == _REFERENCE_ONLY
        if reference_only and not include_reference_only:
            continue
        ranked.append(
            TemplateHit(
                file=str(entry.get("file", "")),
                title=str(entry.get("title", "")),
                group=str(entry.get("group", "")),
                score=score,
                sections_present=list(entry.get("sections_present", [])),
                sections_missing=list(entry.get("sections_missing", [])),
                reference_only=reference_only,
                scrub_pending=False,
                path=str(brain_loader.template_path(str(entry.get("file", "")))),
            )
        )
    # Deterministic ordering: score desc, then filename asc.
    ranked.sort(key=lambda hit: (-hit.score, hit.file))
    return ranked[: max(0, int(limit))]


def reference_only_files() -> list[str]:
    """Filenames the manifest flags ``licence_risk == 'review'``."""
    return [
        str(entry.get("file", ""))
        for entry in brain_loader.templates()
        if str(entry.get("licence_risk", "low")).lower() == _REFERENCE_ONLY
    ]


def clear_caches() -> None:
    available_templates.cache_clear()


__all__ = [
    "LAY_SYNONYMS",
    "SCRUB_PENDING",
    "SELFTEST_QUERIES",
    "TemplateHit",
    "available_templates",
    "clear_caches",
    "normalise",
    "reference_only_files",
    "retrieve",
]

"""Musterbrief retrieval — indication-keyword scoring against ``manifest.json``.

OWNER: WORKSTREAM-BRAIN-V2 (retrieval precision).

Scoring philosophy (the 2026-10-02 precision fix)
------------------------------------------------
Earlier versions scored every token of a template's *title* equally, so a dictation
about a left-lower-abdomen diverticulitis (keywords ``Divertikulitis`` / ``Sigma``)
was outranked by ``Akut auf chronisches Subduralhämatom`` (1.21 vs 1.03) purely
because the short generic token ``auf`` matched *inside* long query words such as
``aufgenommen``.

The scorer now separates signal from noise:

* **Indication keywords and title phrases weigh far more than generic adjectives.**
  A query token that is an exact ``indication_keywords`` hit scores ``6.0``; a title
  token ``5.0``; the filename stem ``4.0``; a controlled substring overlap ``1.2``.
  Generic clinical modifiers (``akut``, ``chronisch``, ``links``, ``stationär`` …,
  see :mod:`briefato.brain.stopwords`) are down-weighted to ``0.15`` — three
  adjectives can never beat one indication keyword.
* **Substring matching is conservative**: both tokens must be at least 6 characters,
  so ``auf`` can no longer match inside ``aufgenommen``.
* **Multi-word phrase hits are rewarded** (a doctation phrase contained in an
  indication keyword / title phrase adds ``4.0`` / ``3.0``).
* **Umlaut/ß normalisation** on both sides.
* Every hit carries a short German *reason* (``Stichwort: Divertikulitis``).

Two hard governance gates are unchanged:

1. **Scrub-pending templates are never retrievable.**
2. **Licence-review templates are returned but flagged ``reference_only=True``.**
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Iterable

from . import brain_loader
from .stopwords import QUALIFIER_WEIGHT, is_qualifier, is_stop

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

# Adversarial regression queries: the correct template must beat any template that
# only shares a generic clinical adjective ("akut", "chronisch", …). The expected
# value is a lowercase filename substring; ``None`` means "assert the top hit shares
# at least one non-generic indication token via the reason". Documented in README.
ADVERSARIAL_QUERIES: tuple[tuple[str, str], ...] = (
    (
        "Die Patientin stellte sich mit seit zwei Tagen bestehenden linksseitigen "
        "Unterbauchschmerzen und Fieber vor. Sonographisch zeigte sich eine entzündlich "
        "verdickte Sigma-Schlinge. Wir nahmen die Patientin zur i.v. Antibiotikatherapie "
        "stationär auf.",
        "divertikulitis",
    ),
    ("Subduralhämatom nach Sturz auf den Kopf", "subduralhaematom"),
    ("Gallensteine mit Kolik und Druckschmerz im rechten Oberbauch", "gallen"),
    ("Leistenhernie Operation nach TAPP", "tapp"),
    ("TVT der linken Beinvene", "tiefe_beinvenenthrombose"),
    ("akute Appendizitis mit rechtsseitigen Unterbauchschmerzen", "append"),
    (
        "chronische Herzinsuffizienz mit kardialer Dekompensation",
        "chronische_herzinsuffizienz",
    ),
    ("akute Cholezystitis mit Oberbauchschmerzen", "cholezystitis"),
    ("akute Pneumonie mit Fieber und Husten", "pneumonie"),
    ("Nierensteine mit Kolik", "urolithiasis"),
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
    "nierensteine": ("urolithiasis",),
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

_REFERENCE_ONLY = "review"

# Scoring weights (documented, tested).
W_KEYWORD = 6.0
W_TITLE = 5.0
W_STEM = 4.0
W_SUBSTRING = 1.2
W_KEYWORD_PHRASE = 4.0
W_TITLE_PHRASE = 3.0
MIN_SUBSTRING_LEN = 6


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


def _content_tokens(text: str, *, min_len: int = 3) -> set[str]:
    """Tokens minus grammatical stopwords — the query-side filter."""
    return {word for word in normalise(text).split() if len(word) >= min_len and not is_stop(word)}


def _phrases(text: str, *, max_len: int = 3) -> set[str]:
    """Normalised n-grams (2..max_len) of the content tokens of ``text``."""
    tokens = normalise(text).split()
    out: set[str] = set()
    for size in range(2, max_len + 1):
        for start in range(0, len(tokens) - size + 1):
            gram = tokens[start : start + size]
            if all(len(part) >= 2 for part in gram):
                out.add(" ".join(gram))
    return out


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
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "title": self.title,
            "score": self.score,
            "group": self.group,
            "reason": self.reason,
            "reference_only": self.reference_only,
            "scrub_pending": self.scrub_pending,
            "sections_present": list(self.sections_present),
        }


@lru_cache(maxsize=1)
def available_templates() -> tuple[dict[str, Any], ...]:
    """Manifest entries that are allowed to be retrieved (scrub-pending removed).

    Each entry gains private ``_kw`` / ``_title`` / ``_stem`` token sets plus the
    corresponding phrase sets used by the scorer.
    """
    kept: list[dict[str, Any]] = []
    for entry in brain_loader.templates():
        if entry.get("file") in SCRUB_PENDING:
            continue
        scored = dict(entry)
        keywords = [str(keyword) for keyword in entry.get("indication_keywords", [])]
        title = str(entry.get("title", ""))
        file_name = str(entry.get("file", ""))
        stem = file_name[:-3] if file_name.endswith(".md") else file_name

        kw_tokens: set[str] = set()
        kw_phrases: set[str] = set()
        for keyword in keywords:
            kw_tokens |= _tokens(keyword)
            normalised = normalise(keyword)
            if " " in normalised:
                kw_phrases.add(normalised)

        scored["_kw"] = kw_tokens
        scored["_kw_phrases"] = kw_phrases
        scored["_title"] = _tokens(title)
        scored["_title_phrases"] = _phrases(title)
        scored["_stem"] = _tokens(stem)
        kept.append(scored)
    return tuple(kept)


def _score(query_tokens: list[str], candidate: dict[str, Any]) -> tuple[float, str]:
    """Score one candidate; return ``(score, German reason)``.

    ``query_tokens`` is already synonym-expanded. Stopwords are ignored; generic
    clinical qualifiers are down-weighted to :data:`QUALIFIER_WEIGHT`.
    """
    kw = candidate["_kw"]
    title = candidate["_title"]
    stem = candidate["_stem"]
    haystack = kw | title | stem

    total = 0.0
    matched = 0
    reason = ""
    reason_weight = -1.0

    for token in query_tokens:
        if is_stop(token):
            continue
        best = 0.0
        why = ""
        if token in kw:
            best, why = W_KEYWORD, f"Stichwort: {token}"
        elif token in title:
            best, why = W_TITLE, f"Titel: {token}"
        elif token in stem:
            best, why = W_STEM, f"Datei: {token}"
        else:
            for other in haystack:
                if (
                    len(token) >= MIN_SUBSTRING_LEN
                    and len(other) >= MIN_SUBSTRING_LEN
                    and (token in other or other in token)
                ):
                    best = max(best, W_SUBSTRING)
                    if not why:
                        why = f"Teiltreffer: {token}"
        if best <= 0:
            continue
        weight = QUALIFIER_WEIGHT if is_qualifier(token) else 1.0
        contribution = best * weight
        total += contribution
        matched += 1
        if contribution > reason_weight:
            reason_weight = contribution
            reason = why

    # Multi-word phrase bonus — a dictation phrase contained in a keyword/title phrase.
    query_phrases = set()
    for size in (2, 3):
        for start in range(0, len(query_tokens) - size + 1):
            gram = query_tokens[start : start + size]
            if all(not is_stop(part) for part in gram):
                query_phrases.add(" ".join(gram))
    for phrase in query_phrases:
        if phrase in candidate["_kw_phrases"]:
            total += W_KEYWORD_PHRASE
            if total > 0 and not reason:
                reason = f"Stichwort: {phrase}"
        elif phrase in candidate["_title_phrases"]:
            total += W_TITLE_PHRASE

    if matched and not reason:
        reason = "Stichworttreffer"
    return round(total, 4), reason


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
    base = [word for word in normalise(query).split() if len(word) >= 3 and not is_stop(word)]
    expanded = _expand(base)
    ranked: list[TemplateHit] = []
    for entry in available_templates():
        score, reason = _score(expanded, entry)
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
                reason=reason,
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
    "ADVERSARIAL_QUERIES",
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

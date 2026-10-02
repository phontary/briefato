"""German stopwords and generic clinical qualifiers for Musterbrief retrieval.

OWNER: WORKSTREAM-BRAIN-V2 (retrieval precision).

The retrieval scorer used to treat every token of a template's title as equal, so
generic clinical adjectives ("akut", "chronisch", "auf") could outrank the
indication-bearing noun phrase ("Divertikulitis", "Sigma") and a dictation about a
left-lower-abdomen diverticulitis was matched to a subdural haematoma template.

This module centralises the two lists that fix that:

* :data:`STOPWORDS` — purely grammatical German function words (der/die/das, bei,
  mit, nach, …). They carry no clinical signal and are dropped from scoring.
* :data:`QUALIFIERS` / :data:`QUALIFIER_PREFIXES` — generic clinical modifiers and
  routing words (akut*, chronisch*, links*, rechts*, stationär*, aufgenommen,
  Patient/in, …). They are *heavily down-weighted* (see
  :data:`qualifier_weight`) so they can never dominate a real indication keyword,
  while still breaking near-ties between two templates of the same entity.

No third-party dependency: stdlib only.
"""

from __future__ import annotations

# --- grammatical function words (never clinical signal) ---------------------
STOPWORDS: frozenset[str] = frozenset(
    {
        "der", "die", "das", "den", "dem", "des", "deren", "dessen",
        "ein", "eine", "einer", "einem", "einen", "eines",
        "und", "oder", "aber", "sowie", "bzw", "beziehungsweise",
        "mit", "ohne", "bei", "nach", "vor", "von", "vom", "aus", "zu", "zur",
        "zum", "im", "in", "am", "an", "auf", "ueber", "über", "unter",
        "fuer", "für", "als", "ist", "sind", "war", "waren", "wird", "werden",
        "wurde", "wurden", "hat", "hatte", "haben", "kann", "koennen", "können",
        "sich", "sowie", "dass", "dies", "diese", "dieser", "dieses",
        "the", "and", "with", "of",
    }
)

# --- generic clinical modifiers / routing words -----------------------------
# Exact tokens (inflected forms the scorer sees verbatim).
QUALIFIERS: frozenset[str] = frozenset(
    {
        "akut", "akute", "akuter", "akutes", "akuten", "akutem",
        "chronisch", "chronische", "chronischer", "chronisches", "chronischen",
        "links", "linke", "linker", "linksseitig", "linksseitige",
        "rechts", "rechte", "rechter", "rechtsseitig", "rechtsseitige",
        "obere", "oberer", "oberes", "untere", "unterer", "unteres",
        "stationaer", "stationaere", "stationaerer", "stationäres", "stationär",
        "stationäre", "stationärer", "ambulant", "ambulante", "ambulanter",
        "aufnahme", "aufgenommen", "aufnahmesituation", "aufnahmegrund",
        "entlassung", "entlassen", "entlassmanagement",
        "patient", "patientin", "patienten", "patientinnen", "pat",
        "frau", "herr", "mann", "person",
        "verlauf", "verlaufskontrolle", "vorstellung", "vorstellig",
        "diagnose", "diagnosen", "befund", "anamnese",
        "klinik", "klinisch", "klinische", "klinischer", "klinisches",
        "therapie", "therapieempfehlung", "therapieempfehlungen",
        "nachsorge", "diagnostik", "untersuchung",
        "wieder", "erneut", "erneute", "erneuter",
        "symptomatik", "beschwerden", "schmerzen",
        "typ", "grad", "stadium",
    }
)

# Prefix stems that mark a qualifier regardless of inflection. Applied only when
# the token has >= 5 characters so short clinical abbreviations are never swallowed.
QUALIFIER_PREFIXES: tuple[str, ...] = (
    "akut",
    "chronisch",
    "linksseit",
    "rechtsseit",
    "stationaer",
    "stationär",
    "ambulant",
    "aufgenomm",
    "entlass",
)

# A qualifier hit counts this fraction of a normal token hit. Small enough that
# three generic adjectives never beat one indication keyword (keyword weight 6.0).
QUALIFIER_WEIGHT = 0.15


def is_stop(token: str) -> bool:
    """True for grammatical function words."""
    return token in STOPWORDS


def is_qualifier(token: str) -> bool:
    """True for generic clinical modifiers / routing words (incl. inflections)."""
    if token in QUALIFIERS:
        return True
    if len(token) >= 5 and any(token.startswith(prefix) for prefix in QUALIFIER_PREFIXES):
        return True
    return False


__all__ = [
    "QUALIFIER_PREFIXES",
    "QUALIFIER_WEIGHT",
    "QUALIFIERS",
    "STOPWORDS",
    "is_qualifier",
    "is_stop",
]

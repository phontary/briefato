"""Department OP standards — selection, prompt skeleton and grounding text.

OWNER: WORKSTREAM-OP-STANDARDS.

Mohamed's Schreibdienst method carries *department standards* for common operations
(the generic standard-step catalogue, the laparoscopic cholecystectomy word-for-word
template, the open Narbenhernie Sublay repair). They were harvested into
``brain/standards/*.md`` (product-owned, provenance-tagged). A dictation that omits
the routine procedural steps must complete them from exactly this method knowledge —
not from a web enrichment, which is why the standard is injected into **every**
OP-Bericht prompt regardless of the optional enrichment toggle.

Public surface used by the pipeline:

    from briefato.brain import standards

    standards.standard_block(doc_type, dictation)      # labelled prompt block (or "")
    standards.standard_reference(doc_type, dictation)  # same text for the rule checker
    standards.select(doc_type, dictation)              # the chosen StandardEntry (or None)

Selection is driven by the machine-readable trigger table in ``brain/standards/index.md``
(the brain owns the keywords; this module only parses it). Only the document type
``operationsbericht`` receives a standard — every other type returns ``""``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from . import brain_loader

# The document type this module serves. Any other type gets no standard block.
STANDARD_DOC_TYPE = "operationsbericht"

# The clearly-labelled prompt block the model must treat as a binding skeleton.
STANDARD_HEADER = "ABTEILUNGSSTANDARD (aus der Methode – verbindliches Gerüst):"
STANDARD_INSTRUCTION = (
    "ANWEISUNG: Nutzen Sie diesen Abteilungsstandard als verbindliches Gerüst für alle "
    "standardgemäßen, routinemäßigen Schritte und übernehmen Sie diese in eigener Formulierung. "
    "Passen Sie ausschließlich patientenbezogene Angaben an (Alter, Geschlecht, OP-Datum, "
    "Situsbefund); alle patientenbezogenen Daten stammen strikt aus dem DIKTAT. Nicht belegte "
    "patientenindividuelle Situsdetails sowie Blutsperren oder Drainagen ohne Dokumentation "
    "ergänzen Sie nicht."
)

# A trigger shorter than this matches on word boundaries only (so "che" never matches
# inside "Chemotherapie"); longer triggers also match inside German compounds
# ("narbenhernie" in "Narbenhernienversorgung").
_SHORT_TRIGGER = 6

_FALLBACK_MARKERS = {"*", "fallback", "standard"}


@dataclass(frozen=True)
class StandardEntry:
    """One department standard: its trigger table row plus the loaded markdown."""

    order: int
    file: str
    triggers: tuple[str, ...]
    fallback: bool
    text: str

    @property
    def name(self) -> str:
        return self.file[:-3] if self.file.endswith(".md") else self.file


def _fold(text: str) -> str:
    """Lowercase + umlaut-fold so ASCII triggers match real German dictation."""
    folded = (text or "").lower()
    for source, target in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        folded = folded.replace(source, target)
    return folded


def _parse_index(text: str) -> tuple[StandardEntry, ...]:
    """Parse the markdown trigger table of ``brain/standards/index.md``."""
    entries: list[StandardEntry] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 3 or not cells[0].isdigit():
            continue  # header / separator / prose row
        order = int(cells[0])
        file_name = cells[1]
        raw_triggers = [item.strip().lower() for item in cells[2].split(",") if item.strip()]
        fallback = any(item in _FALLBACK_MARKERS for item in raw_triggers)
        if not file_name or (not fallback and not raw_triggers):
            continue
        entries.append(
            StandardEntry(
                order=order,
                file=file_name,
                triggers=tuple(raw_triggers),
                fallback=fallback,
                text=brain_loader.standard_text(file_name),
            )
        )
    return tuple(sorted(entries, key=lambda entry: entry.order))


@lru_cache(maxsize=1)
def _entries() -> tuple[StandardEntry, ...]:
    return _parse_index(brain_loader.standards_index_text())


def _matches(trigger: str, folded_dictation: str) -> bool:
    if len(trigger) < _SHORT_TRIGGER:
        escaped = re.escape(trigger)
        return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", folded_dictation) is not None
    return trigger in folded_dictation


def select(doc_type: str, dictation: str = "") -> StandardEntry | None:
    """Return the matching standard for ``doc_type``; ``None`` for other document types."""
    if (doc_type or "").strip().lower() != STANDARD_DOC_TYPE:
        return None
    folded = _fold(dictation)
    entries = _entries()
    fallback: StandardEntry | None = None
    for entry in entries:
        if entry.fallback:
            fallback = fallback or entry
            continue
        if any(_matches(trigger, folded) for trigger in entry.triggers):
            return entry
    return fallback


def standard_text_for(doc_type: str, dictation: str = "") -> str:
    """The raw text of the selected standard (``""`` when the type has none)."""
    entry = select(doc_type, dictation)
    return entry.text if entry is not None else ""


def standard_block(doc_type: str, dictation: str = "") -> str:
    """The labelled ``ABTEILUNGSSTANDARD`` prompt block (``""`` for other types)."""
    text = standard_text_for(doc_type, dictation)
    if not text:
        return ""
    return f"{STANDARD_HEADER}\n{text.strip()}\n{STANDARD_INSTRUCTION}"


def standard_reference(doc_type: str, dictation: str = "") -> str:
    """The standard text passed to the rule checker so its terms count as grounded.

    Without this the routine steps the model legitimately completes from the department
    standard would be reported as hard ``R-INVENT`` instead of the soft ``R-REFERENZ`` note.
    """
    return standard_text_for(doc_type, dictation)


def clear_caches() -> None:
    """Drop the parsed index cache (tests set ``BRIEFATO_BRAIN_DIR`` between cases)."""
    _entries.cache_clear()


__all__ = [
    "STANDARD_DOC_TYPE",
    "STANDARD_HEADER",
    "STANDARD_INSTRUCTION",
    "StandardEntry",
    "clear_caches",
    "select",
    "standard_block",
    "standard_reference",
    "standard_text_for",
]

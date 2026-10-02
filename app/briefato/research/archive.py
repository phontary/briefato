"""ArchiveEnricher — derive standard technique / materials / follow-up from Musterbriefe.

OWNER: WORKSTREAM-ENGINE-V2.

First-choice enrichment backend (kern K7.5: 'bei lückenhaftem OP-Rohmaterial
Standardtechnik/Materialien aus dem Musterbrief ableiten — nicht ad hoc erfinden'). It
reuses the governed retrieval (:mod:`briefato.brain.retrieval`) — scrub-pending templates
can never appear — and reads only the **generic** clinical sections
(``## Therapie`` / ``## Nachsorge`` / ``## Diagnostik``) of the retrieved templates.

Licence-review templates (``reference_only=True``) contribute *structure only*: their
prose is never copied into an enrichment (the same rule the prompt assembly enforces).
Each derived statement carries the Musterbrief filename as its ``source``.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from ..brain import brain_loader, retrieval
from .base import Enrichment, filter_generic

_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_LINE_CLEAN_RE = re.compile(r"^\s*(?:[-*•·]|\d+[.)])\s*")

# Musterbrief section -> (enrichment kind, how many candidate lines to take).
_SECTION_KIND: dict[str, tuple[str, int]] = {
    "Therapie": ("technique", 3),
    "Nachsorge": ("follow_up", 2),
    "Therapieempfehlungen bei Entlassung": ("follow_up", 2),
    "Diagnostik": ("diagnostics", 1),
}

_MATERIAL_WORDS = (
    "naht", "faden", "netz", "mesh", "prothese", "implantat", "titan", "platte", "schraube",
    "drainage", "drain", "stapler", "clip", "katheter", "schraub", "zement", "patch",
    "shunt", "stent", "ballon", "marknagel", "kirschner", "cerclage", "pins",
)
_MEDICATION_CLASS_WORDS = (
    "nsar", "antibiotik", "antibiotika", "ppi", "protonenpumpen", "heparin", "nmh",
    "doac", "antikoagul", "thromboseprophylaxe", "analgetik", "opioid", "insulin",
    "metformin", "statine", "beta", "ace-hemmer", "diuretik",
)
_FOLLOW_UP_WORDS = (
    "woche", "wochen", "monat", "monate", "intervall", "nachsorge", "kontrolle",
    "verlaufskontrolle", "fadenzug", "r(?:oe|ö)ntgenkontrolle", "metallentfernung",
)


def _split_sections(raw: str) -> dict[str, str]:
    parts = _SECTION_RE.split(raw or "")
    sections: dict[str, str] = {}
    for index in range(1, len(parts) - 1, 2):
        sections[parts[index].strip()] = parts[index + 1].strip("\n")
    return sections


def _candidate_lines(body: str) -> list[str]:
    lines: list[str] = []
    for raw_line in (body or "").splitlines():
        line = _LINE_CLEAN_RE.sub("", raw_line).strip()
        line = " ".join(line.split())
        if len(line) < 20:
            continue
        if line.endswith(":") and len(line) < 60:
            continue
        lines.append(line)
    return lines


def _refine_kind(line: str, default: str) -> str:
    lowered = line.lower()
    # A follow-up action ("Wundkontrolle … nach 10 Tagen", "Fadenzug") takes precedence
    # over an incidental material word in the same line.
    if re.search(r"(?i)" + "|".join(_FOLLOW_UP_WORDS), lowered):
        return "follow_up"
    if any(word in lowered for word in _MATERIAL_WORDS):
        return "materials"
    if any(word in lowered for word in _MEDICATION_CLASS_WORDS):
        return "medication_class"
    return default


class ArchiveEnricher:
    """Derive generic standard knowledge from the retrieved Musterbriefe."""

    origin = "archive"

    def __init__(
        self,
        *,
        retrieve_fn: Callable[..., list[Any]] | None = None,
        read_template_fn: Callable[[str], str] | None = None,
        retrieval_limit: int = 4,
    ) -> None:
        self._retrieve = retrieve_fn or retrieval.retrieve
        self._read_template = read_template_fn or brain_loader.read_template
        self._retrieval_limit = int(retrieval_limit)

    def enrich(
        self,
        *,
        doc_type: str,
        context_text: str,
        patient_context: dict[str, str] | None = None,
        dictation: str = "",
        max_items: int = 6,
    ) -> list[Enrichment]:
        try:
            hits = self._retrieve(context_text or "", limit=self._retrieval_limit)
        except Exception:  # pragma: no cover - retrieval is read-only and total
            hits = []

        candidates: list[Enrichment] = []
        for hit in hits:
            # Licence-review templates: structure only, never their prose.
            if getattr(hit, "reference_only", False):
                continue
            file_name = str(getattr(hit, "file", "") or "")
            if not file_name:
                continue
            try:
                raw = self._read_template(file_name)
            except Exception:
                continue
            sections = _split_sections(raw)
            for section_name, (default_kind, quota) in _SECTION_KIND.items():
                body = sections.get(section_name)
                if not body:
                    continue
                taken = 0
                for line in _candidate_lines(body):
                    if taken >= quota or len(candidates) >= max_items * 3:
                        break
                    candidates.append(
                        Enrichment(
                            statement=line,
                            source=file_name,
                            kind=_refine_kind(line, default_kind),
                            origin="archive",
                            score=float(getattr(hit, "score", 0.0) or 0.0),
                        )
                    )
                    taken += 1
        kept, _blocked = filter_generic(candidates, patient_context=patient_context, dictation=dictation)
        return kept[: max(0, int(max_items))]


__all__ = ["ArchiveEnricher"]

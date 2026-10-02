"""Grounded enrichment — the 'Improvisation' backend (Musterbrief archive first, web optional).

OWNER: WORKSTREAM-ENGINE-V2.

Public surface used by the pipeline:

    from briefato.research import get_research_provider, Enrichment, filter_generic

``get_research_provider()`` returns a :class:`GroundedEnricher` that always tries the
Musterbrief archive first and only consults the optional SearXNG web backend when
``BRIEFATO_RESEARCH_BASE_URL`` is configured. If research is off/unavailable it degrades to
:class:`~briefato.research.base.NullEnricher` behaviour (an empty list) — the letter is
still produced without enrichment.
"""

from __future__ import annotations

from typing import Any, Sequence

from .archive import ArchiveEnricher
from .base import (
    Enrichment,
    NullEnricher,
    ResearchProvider,
    enrich_default,
    filter_generic,
    is_generic_statement,
    research_base_url,
)
from .web import RESEARCH_DOMAINS, WebEnricher


class GroundedEnricher:
    """Archive-first enrichment, optionally supplemented by restricted web research."""

    def __init__(self, archive: ResearchProvider | None = None, web: ResearchProvider | None = None) -> None:
        self._archive = archive if archive is not None else ArchiveEnricher()
        self._web = web

    @property
    def archive(self) -> ResearchProvider | None:
        return self._archive

    @property
    def web(self) -> ResearchProvider | None:
        return self._web

    def enrich(
        self,
        *,
        doc_type: str,
        context_text: str,
        patient_context: dict[str, str] | None = None,
        dictation: str = "",
        max_items: int = 6,
    ) -> list[Enrichment]:
        items: list[Enrichment] = []
        if self._archive is not None:
            items.extend(
                self._archive.enrich(
                    doc_type=doc_type,
                    context_text=context_text,
                    patient_context=patient_context,
                    dictation=dictation,
                    max_items=max_items,
                )
            )
        # Web research only supplements what the archive did not answer.
        if self._web is not None and len(items) < max_items:
            items.extend(
                self._web.enrich(
                    doc_type=doc_type,
                    context_text=context_text,
                    patient_context=patient_context,
                    dictation=dictation,
                    max_items=max_items - len(items),
                )
            )
        kept, _blocked = filter_generic(items, patient_context=patient_context, dictation=dictation)
        return kept[: max(0, int(max_items))]


def get_research_provider(
    settings: Any = None,
    *,
    base_url: str | None = None,
    web: ResearchProvider | None = None,
    web_client: Any = None,
) -> ResearchProvider:
    """Build the default research provider for this request.

    Archive enrichment is always available (it is pure local I/O). The web backend is only
    attached when a base URL is configured (argument or ``BRIEFATO_RESEARCH_BASE_URL``).
    """
    archive = ArchiveEnricher()
    effective_base = (base_url if base_url is not None else research_base_url()).strip()
    if web is None and effective_base:
        web = WebEnricher(effective_base, client=web_client)
    return GroundedEnricher(archive=archive, web=web)


def enrich_if_enabled(
    provider: ResearchProvider,
    *,
    doc_type: str,
    context_text: str,
    patient_context: dict[str, str] | None = None,
    dictation: str = "",
    max_items: int = 6,
) -> list[Enrichment]:
    """Call ``provider`` and keep only statements that pass the generic guardrail."""
    try:
        raw = provider.enrich(
            doc_type=doc_type,
            context_text=context_text,
            patient_context=patient_context,
            dictation=dictation,
            max_items=max_items,
        )
    except Exception:  # pragma: no cover - research must never break generation
        return []
    kept, _blocked = filter_generic(raw, patient_context=patient_context, dictation=dictation)
    return kept


__all__ = [
    "ArchiveEnricher",
    "Enrichment",
    "GroundedEnricher",
    "NullEnricher",
    "RESEARCH_DOMAINS",
    "ResearchProvider",
    "WebEnricher",
    "enrich_default",
    "enrich_if_enabled",
    "filter_generic",
    "get_research_provider",
    "is_generic_statement",
    "research_base_url",
]

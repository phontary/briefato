"""WebEnricher — optional SearXNG research restricted to reputable medical domains.

OWNER: WORKSTREAM-ENGINE-V2.

Only active when ``BRIEFATO_RESEARCH_BASE_URL`` is set (a SearXNG instance is available on
the host at ``127.0.0.1:8088`` — reachable as ``http://searxng:8080/`` on the shared docker
network). The query is restricted to reputable domains with ``site:`` operators:

    awmf.org, pubmed.ncbi.nlm.nih.gov, doccheck.com, msdmanuals.com, leitlinien.de, bfarm.de

Every returned snippet becomes one :class:`Enrichment` whose ``source`` is the result URL.
The generic-knowledge guardrail (:func:`briefato.research.base.filter_generic`) is applied
before the snippets are surfaced. No network call happens in tests: a ``fetch`` callable or
an ``httpx.Client`` (with a mock transport) can be injected.
"""

from __future__ import annotations

import re
from typing import Any, Callable

import httpx

from .base import Enrichment, filter_generic

#: Reputable domains the web research is restricted to (with ``site:`` operators).
RESEARCH_DOMAINS: tuple[str, ...] = (
    "awmf.org",
    "pubmed.ncbi.nlm.nih.gov",
    "doccheck.com",
    "msdmanuals.com",
    "leitlinien.de",
    "bfarm.de",
)

_QUERY_STOPWORDS = {
    "der", "die", "das", "und", "oder", "mit", "bei", "von", "den", "dem", "des", "ein",
    "eine", "einer", "auf", "aus", "für", "ist", "war", "wird", "wurde", "sich", "nach",
    "über", "unter", "im", "in", "am", "an", "zu", "zur", "zum", "als", "auch", "kein",
    "keine", "ohne", "sowie", "bzw",
}


def _query_terms(context_text: str, *, limit: int = 8) -> list[str]:
    words = re.findall(r"[A-Za-zÄÖÜäöüßä]{4,}", context_text or "")
    seen: list[str] = []
    for word in words:
        low = word.lower()
        if low in _QUERY_STOPWORDS or low in seen:
            continue
        seen.append(low)
        if len(seen) >= limit:
            break
    return seen


class WebEnricher:
    """SearXNG-backed enrichment, restricted to the reputable-domain allow-list."""

    origin = "web"

    def __init__(
        self,
        base_url: str,
        *,
        fetch: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
        client: httpx.Client | None = None,
        timeout: float = 8.0,
        domains: tuple[str, ...] = RESEARCH_DOMAINS,
        max_results: int = 6,
    ) -> None:
        self._base_url = str(base_url or "").rstrip("/")
        self._fetch = fetch
        self._client = client
        self._timeout = float(timeout)
        self._domains = tuple(domains)
        self._max_results = int(max_results)

    # -- transport ---------------------------------------------------------

    def _request(self, query: str) -> dict[str, Any]:
        params = {
            "q": query,
            "format": "json",
            "language": "de",
            "safesearch": 1,
            "categories": "general",
        }
        url = self._base_url + "/search"
        if self._fetch is not None:
            return self._fetch(url, params)
        if self._client is not None:
            response = self._client.get(url, params=params, timeout=self._timeout)
        else:
            response = httpx.get(url, params=params, timeout=self._timeout)
        response.raise_for_status()
        return response.json()

    def build_query(self, context_text: str) -> str:
        terms = _query_terms(context_text)
        core = " ".join(terms) or "Standardoperation Technik"
        sites = " OR ".join(f"site:{domain}" for domain in self._domains)
        return f"{core} ({sites})"

    # -- provider API ------------------------------------------------------

    def enrich(
        self,
        *,
        doc_type: str,
        context_text: str,
        patient_context: dict[str, str] | None = None,
        dictation: str = "",
        max_items: int = 6,
    ) -> list[Enrichment]:
        if not self._base_url:
            return []
        try:
            payload = self._request(self.build_query(context_text))
        except Exception:
            return []

        results = payload.get("results") if isinstance(payload, dict) else None
        candidates: list[Enrichment] = []
        for entry in (results or [])[: self._max_results]:
            if not isinstance(entry, dict):
                continue
            snippet = " ".join(str(entry.get("content") or "").split())
            url = str(entry.get("url") or "")
            if not snippet or not url:
                continue
            candidates.append(
                Enrichment(
                    statement=snippet,
                    source=url,
                    kind="standard",
                    origin="web",
                    score=1.0,
                )
            )
        kept, _blocked = filter_generic(candidates, patient_context=patient_context, dictation=dictation)
        return kept[: max(0, int(max_items))]


__all__ = ["RESEARCH_DOMAINS", "WebEnricher"]

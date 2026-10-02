"""Corpus loading + validation for the Briefato quality harness.

A case is one JSON file under ``tools/eval/cases/`` with the shape::

    {
      "id": "entlassbrief-01",
      "doc_type": "arztbrief",                 # expected document type
      "title": "Stationärer Entlassbrief …",
      "sources": [{"label": "Sono", "text": "…"}, …],   # messy KIS raw material
      "dictation": "…",                        # input sent to the pipeline
      "must_contain": ["…"],                   # human quality expectations
      "must_not_contain": ["…"],
      "expected_blocks": ["Diagnosen:", …],    # ordered block expectations
      "notes": "…"
    }

No real patient data may appear: names are invented (``Muster, Anna``) or the
placeholder ``XXX`` is used.

Pure stdlib.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CASES_DIR = Path(__file__).resolve().parent / "cases"

REQUIRED_KEYS = ("id", "doc_type", "title", "dictation")
LIST_KEYS = ("must_contain", "must_not_contain", "expected_blocks")


class CorpusError(RuntimeError):
    """A case file is missing or malformed."""


@dataclass(frozen=True)
class Source:
    label: str
    text: str


@dataclass(frozen=True)
class Case:
    id: str
    doc_type: str
    title: str
    sources: tuple[Source, ...]
    dictation: str
    must_contain: tuple[str, ...] = field(default_factory=tuple)
    must_not_contain: tuple[str, ...] = field(default_factory=tuple)
    expected_blocks: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""
    path: str = ""

    def sources_block(self) -> str:
        """Render the raw sources as one labelled block (used by ``--enrich``)."""
        parts: list[str] = []
        for source in self.sources:
            parts.append(f"{source.label}: {source.text}".strip())
        return "\n".join(parts)


def _coerce_case(data: dict, path: Path) -> Case:
    for key in REQUIRED_KEYS:
        if key not in data or not str(data.get(key) or "").strip():
            raise CorpusError(f"{path.name}: missing required key {key!r}")

    sources_raw = data.get("sources") or []
    if not isinstance(sources_raw, list):
        raise CorpusError(f"{path.name}: 'sources' must be a list")
    sources: list[Source] = []
    for entry in sources_raw:
        if not isinstance(entry, dict) or "text" not in entry:
            raise CorpusError(f"{path.name}: each source needs a 'text' field")
        sources.append(Source(label=str(entry.get("label") or "Quelle"), text=str(entry["text"])))

    def _list(key: str) -> tuple[str, ...]:
        value = data.get(key) or []
        if not isinstance(value, list):
            raise CorpusError(f"{path.name}: {key!r} must be a list")
        return tuple(str(item) for item in value)

    return Case(
        id=str(data["id"]),
        doc_type=str(data["doc_type"]),
        title=str(data["title"]),
        sources=tuple(sources),
        dictation=str(data["dictation"]),
        must_contain=_list("must_contain"),
        must_not_contain=_list("must_not_contain"),
        expected_blocks=_list("expected_blocks"),
        notes=str(data.get("notes") or ""),
        path=str(path),
    )


def load_cases(cases_dir: Path | str | None = None, *, only: list[str] | None = None) -> list[Case]:
    """Load every ``*.json`` case (sorted by id), optionally filtered to ``only`` ids."""
    directory = Path(cases_dir) if cases_dir else DEFAULT_CASES_DIR
    if not directory.is_dir():
        raise CorpusError(f"cases directory not found: {directory}")

    cases: list[Case] = []
    seen: set[str] = set()
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CorpusError(f"{path.name}: invalid JSON: {exc}") from exc
        case = _coerce_case(data, path)
        if case.id in seen:
            raise CorpusError(f"duplicate case id: {case.id}")
        seen.add(case.id)
        cases.append(case)

    if not cases:
        raise CorpusError(f"no cases found in {directory}")

    if only:
        wanted = {item.strip() for item in only if item.strip()}
        filtered = [case for case in cases if case.id in wanted]
        unknown = wanted - {case.id for case in filtered}
        if unknown:
            raise CorpusError(f"unknown case id(s): {', '.join(sorted(unknown))}")
        cases = filtered
    return cases


__all__ = ["Case", "CorpusError", "DEFAULT_CASES_DIR", "Source", "load_cases"]

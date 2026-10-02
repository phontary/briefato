"""Merge near-duplicate Musterbriefe into one product template.

OWNER: WORKSTREAM-BRAIN-V2 (merge task).

The *read-only* Schreibdienst archive (``/workspace/schreibdienst/musterbriefe``)
is never modified. The merge happens only in the packaged product copy
(``brain/musterbriefe/templates/``), driven by ``brain/merges/merge-map.json``.

For every group the builder:

1. reads the group's ``sources`` (primary first), splitting each file into
   ``## `` sections;
2. maps each source heading onto a canonical reference section using the same
   rules as ``brain/musterbriefe/build_library.py``;
3. merges the four clinical sections **Klinik / Diagnostik / Therapie / Nachsorge**
   by concatenating every member's statements and dropping only exact/near-identical
   duplicates (so every distinct clinical statement survives);
4. preserves ``## Quellen`` verbatim when present;
5. appends any remaining section (KU, Verlauf, Diagnosen, OP, Anamnese …) so no
   statement is lost — the "four sections only" instruction is read as the *merge
   scope*, not as permission to delete content.

Output is deterministic (no timestamps), so ``tools/pack-brain.py --check`` can
regenerate and byte-compare it.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import brain_loader

MERGE_MAP_REL = ("merges", "merge-map.json")

# Canonical section resolution — mirrors brain/musterbriefe/build_library.py.
CANON_RULES: list[tuple[str, str]] = [
    (r"quellen|literatur|referenz", "Quellen"),
    (r"^ku\b|ku[- ]befund|koerperliche untersuchung|klinische untersuchung|^untersuchungsbefunde", "KU"),
    (
        r"therapieempfehlung|empfehlungen bei entlassung|therapie bei entlassung|"
        r"ambulante therapieempfehlung|^entlassung$",
        "Therapieempfehlungen bei Entlassung",
    ),
    (r"^nachsorge", "Nachsorge"),
    (r"^verlauf|klassischer verlauf|postoperativer verlauf|verlaufskriterien|op chronologie|operativer verlauf", "Verlauf"),
    (r"^therapie|therapieanpassung|^indikation", "Therapie"),
    (r"^diagnostik|^bildgebung|bildgebende befunde|^radiologie|^pathologie", "Diagnostik"),
    (r"^diagnosen|^icd", "Diagnosen"),
    (
        r"^klinik|klinisches bild|klinische praesentation|klinischer befund|leitsymptome|"
        r"charakteristika|^beschreibung|aufnahmesituation|aufnahmegrund|aufnahmebegruendung",
        "Klinik",
    ),
    (r"^anamnese|anamnese /|/ unfallhergang", "Anamnese"),
    (r"^op$|^op |operationstechnik|^op-", "OP"),
]

# Merge-scope order. The four clinical sections first, then Quellen, then the rest.
PRIMARY_ORDER = ("Klinik", "Diagnostik", "Therapie", "Nachsorge")
REFERENCE_ORDER = (
    "Klinik",
    "KU",
    "Diagnostik",
    "Therapie",
    "Verlauf",
    "Nachsorge",
    "Therapieempfehlungen bei Entlassung",
    "Diagnosen",
    "Quellen",
)

# Heading -> canonical bucket for the four merged sections.
_CANON_SET = {"Klinik", "Diagnostik", "Therapie", "Nachsorge"}


def _norm(text: str) -> str:
    text = (text or "").lower()
    for source, target in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(source, target)
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _canonical(heading: str) -> str:
    heading_norm = _norm(heading)
    for pattern, canonical in CANON_RULES:
        if re.search(pattern, heading_norm):
            return canonical
    return heading.strip()


def _split_sections(raw: str) -> list[tuple[str, str]]:
    if raw.startswith("---"):
        match = re.match(r"^---\n.*?\n---\n?", raw, re.S)
        if match:
            raw = raw[match.end() :]
    parts = re.split(r"^##\s+(.+?)\s*$", raw, flags=re.MULTILINE)
    sections: list[tuple[str, str]] = []
    for index in range(1, len(parts) - 1, 2):
        sections.append((parts[index].strip(), parts[index + 1].strip("\n")))
    return sections


def _line_key(line: str) -> str:
    return _norm(line)


def _near_duplicate(a: str, b: str) -> bool:
    """Conservative near-duplicate test used to drop duplicated statements."""
    if not a or not b:
        return False
    if a == b:
        return True
    return (a in b or b in a) and min(len(a), len(b)) >= 20 and min(len(a), len(b)) / max(len(a), len(b)) >= 0.8


def _merge_lines(chunks: list[str]) -> str:
    """Concatenate section bodies, dropping exact/near-identical lines."""
    kept: list[str] = []
    keys: list[str] = []
    for chunk in chunks:
        for line in chunk.splitlines():
            stripped = line.rstrip()
            key = _line_key(stripped)
            if not key:
                if kept and kept[-1] != "":
                    kept.append("")
                continue
            if any(_near_duplicate(key, existing) for existing in keys):
                continue
            kept.append(stripped)
            keys.append(key)
    while kept and kept[-1] == "":
        kept.pop()
    return "\n".join(kept)


@dataclass
class MergeGroup:
    id: str
    file: str
    title: str
    sources: list[str]
    reason: str = ""
    non_merge_reason: str = ""
    absorbed: list[str] = field(default_factory=list)


@lru_cache(maxsize=1)
def merge_map_path() -> Path:
    return brain_loader.brain_root().joinpath(*MERGE_MAP_REL)


def load_merge_map() -> dict[str, Any]:
    path = merge_map_path()
    if not path.is_file():
        return {"groups": [], "non_merges": []}
    return json.loads(path.read_text(encoding="utf-8"))


def groups() -> list[MergeGroup]:
    out: list[MergeGroup] = []
    for raw in load_merge_map().get("groups", []):
        sources = [str(name) for name in raw.get("sources", [])]
        file_name = str(raw.get("file") or (sources[0] if sources else ""))
        absorbed = [name for name in sources if name != file_name]
        out.append(
            MergeGroup(
                id=str(raw.get("id", "")),
                file=file_name,
                title=str(raw.get("title", "")),
                sources=sources,
                reason=str(raw.get("reason", "")),
                non_merge_reason=str(raw.get("non_merge_reason", "")),
                absorbed=absorbed,
            )
        )
    return out


def group_for_file(file_name: str) -> MergeGroup | None:
    for group in groups():
        if file_name in group.sources or file_name == group.file:
            return group
    return None


def absorbed_files() -> set[str]:
    absorbed: set[str] = set()
    for group in groups():
        absorbed.update(group.absorbed)
    return absorbed


def _read_source(source_dir: Path, name: str) -> str:
    path = source_dir / name
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def build_merged_content(source_dir: Path, group: MergeGroup) -> str:
    """Return the deterministic merged markdown for ``group``."""
    buckets: dict[str, list[str]] = {}
    order: list[str] = []
    for name in group.sources:
        raw = _read_source(source_dir, name)
        for heading, content in _split_sections(raw):
            canonical = _canonical(heading)
            key = canonical if canonical in _CANON_SET or canonical == "Quellen" else heading.strip()
            if key not in buckets:
                buckets[key] = []
                order.append(key)
            buckets[key].append(content)

    lines: list[str] = ["---", "type: Reference", f"title: {group.title}", f"description: Musterbrief: {group.title}",
                        "tags: [Musterbrief, Schreibdienst, merged]",
                        "merged_from: [" + ", ".join(group.sources) + "]", "---", "", f"# {group.title}", ""]

    def render(key: str) -> None:
        body = _merge_lines(buckets[key])
        if not body:
            return
        lines.append(f"## {key}")
        lines.append(body)
        lines.append("")

    for key in PRIMARY_ORDER:
        if key in buckets:
            render(key)
    remaining = [key for key in order if key not in PRIMARY_ORDER]
    for key in remaining:
        render(key)
    return "\n".join(lines).rstrip() + "\n"


def merged_entry(source_dir: Path, group: MergeGroup, base_entries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Build the manifest entry for a merged group."""
    primary = base_entries.get(group.sources[0], {}) if group.sources else {}
    keywords: list[str] = []
    seen: set[str] = set()
    sections: list[str] = []

    def add_keyword(keyword: str) -> None:
        keyword = str(keyword)
        if keyword and keyword not in seen:
            seen.add(keyword)
            keywords.append(keyword)

    for name in group.sources:
        entry = base_entries.get(name, {})
        for keyword in entry.get("indication_keywords", []):
            add_keyword(keyword)
        add_keyword(entry.get("title", ""))
        for section in entry.get("sections_present", []):
            if section not in sections:
                sections.append(section)

    ordered_sections = [section for section in REFERENCE_ORDER if section in sections]
    ordered_sections += [section for section in sections if section not in ordered_sections]
    missing = [section for section in REFERENCE_ORDER if section not in ordered_sections]

    content = build_merged_content(source_dir, group)
    licence_risk = "low"
    for name in group.sources:
        if str(base_entries.get(name, {}).get("licence_risk", "low")).lower() == "review":
            licence_risk = "review"

    return {
        "file": group.file,
        "title": group.title or str(primary.get("title", group.file)),
        "group": str(primary.get("group", "")),
        "indication_keywords": keywords,
        "sections_present": ordered_sections,
        "sections_missing": missing,
        "headings_raw": ordered_sections,
        "has_quellen": "Quellen" in ordered_sections,
        "licence_risk": licence_risk,
        "chars": len(content),
        "body_chars": len(content),
        "merged_from": list(group.absorbed),
        "merged_group": group.id,
    }


def apply_merges(
    templates: list[dict[str, Any]], source_dir: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return ``(effective_entries, stats)`` with merge groups applied.

    ``templates`` is the raw manifest template list. Every group's ``sources`` and
    output ``file`` are removed from the base list and replaced by one merged entry.
    Idempotent: running twice against an already-merged manifest reproduces the same
    effective list, because the group output file is removed before re-adding.
    """
    base = {str(entry.get("file", "")): entry for entry in templates}
    existing_merged = {
        str(entry.get("file", "")): entry for entry in templates if entry.get("merged_from")
    }
    removed: set[str] = set()
    merged: list[dict[str, Any]] = []
    for group in groups():
        removed.update(group.sources)
        removed.add(group.file)
        # Reuse an already-merged entry so re-running the packer never loses the
        # folded absorbed synonyms / licence flag (the source manifest no longer
        # contains the absorbed entries after the first run).
        if group.file in existing_merged:
            merged.append(dict(existing_merged[group.file]))
        else:
            merged.append(merged_entry(source_dir, group, base))
    kept = [dict(entry) for entry in templates if str(entry.get("file", "")) not in removed]
    effective = sorted(kept + merged, key=lambda entry: str(entry.get("file", "")))
    stats = {
        "merged_groups": len(groups()),
        "files_absorbed": len(absorbed_files()),
        "files_removed": len(removed),
    }
    return effective, stats


__all__ = [
    "MergeGroup",
    "REFERENCE_ORDER",
    "absorbed_files",
    "apply_merges",
    "build_merged_content",
    "group_for_file",
    "groups",
    "load_merge_map",
    "merge_map_path",
    "merged_entry",
]

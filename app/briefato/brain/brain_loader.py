"""Cached loaders for the harvested Briefato brain (``/workspace/briefato/brain``).

OWNER: WORKSTREAM-BRAIN-WIRING.

The brain is a set of German markdown knowledge files extracted from Mohamed's real
Schreibdienst profile. It is an *input*, never edited by code:

    brain/
      kern.md                       the method (what to rewrite, how)
      regelwerk.md                  R1..R67 — one testable rule per line
      ANTI-PATTERNS.md              AP-01..AP-25 — forbidden generic-LLM behaviour
      stolperfallen.md              60 pitfalls
      regeln-aus-praxis.md          64 practice rules
      dokumenttypen/*.md            9 document-type playbooks
      musterbriefe/manifest.json    152 template metadata entries + source path

This module resolves the brain directory, fails loudly when it is missing, and
caches every file so the pipeline can assemble a prompt on each request without
re-reading 436 KB from disk.

Resolution order for the brain root:

1. ``BRIEFATO_BRAIN_DIR`` environment variable (a "setting" that needs no change
   to the frozen ``config.Settings`` — see README for why);
2. ``<repo>/brain`` where ``<repo>`` is three levels above this package
   (``app/briefato/brain/brain_loader.py`` -> ``/workspace/briefato``);
3. the nearest ancestor of this package that contains ``brain/kern.md``.

A missing directory or file raises :class:`BrainNotFound` with the exact path that
was looked for — never a silent empty fallback.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

BRAIN_VERSION_FALLBACK = "unknown"

# Playbook files that exist under ``brain/dokumenttypen``. ``entlassbrief`` is the
# routing playbook; the rest are output playbooks.
DOKUMENTTYPEN: dict[str, str] = {
    "arztbrief": "arztbrief.md",
    "zusammenfassung": "zusammenfassung.md",
    "operationsbericht": "operationsbericht.md",
    "ambulant": "ambulant.md",
    "entlassbrief": "entlassbrief.md",
    "pflegebericht": "pflegebericht.md",
    "entlassmedikationsplan": "entlassmedikationsplan.md",
    "ablehnungsbogen": "ablehnungsbogen.md",
    "weiterbildung-kv-nachweise": "weiterbildung-kv-nachweise.md",
}

# Human labels for the UI / letter titles.
DOKUMENTTYP_LABELS: dict[str, str] = {
    "arztbrief": "Arztbrief",
    "zusammenfassung": "Zusammenfassung",
    "operationsbericht": "OP-Bericht",
    "ambulant": "Ambulanter Brief",
    "entlassbrief": "Entlassbrief",
    "pflegebericht": "Pflegebericht-Integration",
    "entlassmedikationsplan": "Entlassmedikationsplan",
    "ablehnungsbogen": "Ablehnungsbogen",
    "weiterbildung-kv-nachweise": "Weiterbildungs-/KV-Nachweis",
}


class BrainError(RuntimeError):
    """Base class for brain loading problems."""


class BrainNotFound(BrainError):
    """The brain directory (or a required file inside it) could not be located."""


@dataclass(frozen=True)
class Rule:
    """One parsed line of ``regelwerk.md``."""

    id: str
    text: str
    provenance: str


_RULE_RE = re.compile(r"^R(\d+):\s*(.*?)\s*—\s*Provenienz:\s*(.*)$")


# --------------------------------------------------------------------------- root


def _candidate_roots() -> list[Path]:
    candidates: list[Path] = []

    env = os.environ.get("BRIEFATO_BRAIN_DIR", "").strip()
    if env:
        candidates.append(Path(env).expanduser())

    # app/briefato/brain/brain_loader.py -> parents[3] == repository root
    here = Path(__file__).resolve()
    if len(here.parents) >= 4:
        candidates.append(here.parents[3] / "brain")

    # Fallback: walk up looking for a directory that contains brain/kern.md.
    for parent in here.parents:
        candidates.append(parent / "brain")

    # De-duplicate while preserving order.
    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def brain_root() -> Path:
    """Return the resolved brain directory.

    If ``BRIEFATO_BRAIN_DIR`` is set it is authoritative: a missing/invalid target
    raises immediately (no silent fallback). Otherwise the repo-relative default and
    an ancestor search are tried. Raises :class:`BrainNotFound` listing every location
    that was tried.
    """
    env = os.environ.get("BRIEFATO_BRAIN_DIR", "").strip()
    if env:
        candidate = Path(env).expanduser()
        if candidate.is_dir() and (candidate / "kern.md").is_file():
            return candidate
        raise BrainNotFound(
            f"BRIEFATO_BRAIN_DIR is set to {candidate} but no 'kern.md' was found there."
        )

    tried = _candidate_roots()
    for candidate in tried:
        if candidate.is_dir() and (candidate / "kern.md").is_file():
            return candidate
    locations = "\n  - ".join(str(path) for path in tried)
    raise BrainNotFound(
        "Briefato brain directory not found (no 'kern.md'). Set BRIEFATO_BRAIN_DIR "
        f"or place the brain next to the app. Tried:\n  - {locations}"
    )


def _read(name: str) -> str:
    root = brain_root()
    path = root / name
    if not path.is_file():
        raise BrainNotFound(f"brain file missing: {path}")
    return path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- cached loaders


@lru_cache(maxsize=1)
def kern_text() -> str:
    return _read("kern.md")


@lru_cache(maxsize=1)
def regelwerk_text() -> str:
    return _read("regelwerk.md")


@lru_cache(maxsize=1)
def anti_patterns_text() -> str:
    return _read("ANTI-PATTERNS.md")


@lru_cache(maxsize=1)
def stolperfallen_text() -> str:
    return _read("stolperfallen.md")


@lru_cache(maxsize=1)
def regeln_aus_praxis_text() -> str:
    return _read("regeln-aus-praxis.md")


@lru_cache(maxsize=None)
def dokumenttyp_text(doc_type: str) -> str:
    """Return the playbook text for ``doc_type`` (see :data:`DOKUMENTTYPEN`)."""
    filename = DOKUMENTTYPEN.get(doc_type)
    if filename is None:
        raise BrainError(f"unknown document type: {doc_type!r}")
    return _read(f"dokumenttypen/{filename}")


# --------------------------------------------------------------------------- standards
#
# Product-owned department standards for the Operationsbericht
# (``brain/standards/*.md``). They are harvested from Mohamed's Schreibdienst method, not
# from the Musterbrief archive, and are injected into every OP-Bericht prompt as a
# labelled skeleton — independently of the optional enrichment toggle.

STANDARDS_DIRNAME = "standards"
STANDARDS_INDEX = "index.md"


@lru_cache(maxsize=1)
def standards_index_text() -> str:
    """Return ``brain/standards/index.md`` (trigger keyword table)."""
    return _read(f"{STANDARDS_DIRNAME}/{STANDARDS_INDEX}")


@lru_cache(maxsize=None)
def standard_text(file_name: str) -> str:
    """Return one department standard ``brain/standards/<file_name>``."""
    name = (file_name or "").strip()
    if not name:
        raise BrainError("empty standard file name")
    return _read(f"{STANDARDS_DIRNAME}/{name}")


@lru_cache(maxsize=1)
def manifest() -> dict[str, Any]:
    """Return the parsed ``musterbriefe/manifest.json``."""
    root = brain_root()
    path = root / "musterbriefe" / "manifest.json"
    if not path.is_file():
        raise BrainNotFound(f"brain manifest missing: {path}")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def templates() -> list[dict[str, Any]]:
    """Return the raw manifest template entries (a fresh shallow copy)."""
    return [dict(entry) for entry in manifest().get("templates", [])]


@lru_cache(maxsize=1)
def musterbriefe_dir() -> Path:
    """Directory holding the actual ``*.md`` Musterbriefe.

    Overridable with ``BRIEFATO_MUSTERBRIEFE_DIR``; otherwise the manifest's
    ``source`` field, which points at the read-only Schreibdienst archive.
    """
    env = os.environ.get("BRIEFATO_MUSTERBRIEFE_DIR", "").strip()
    if env:
        return Path(env).expanduser()
    source = manifest().get("source")
    if source:
        return Path(source)
    return brain_root() / "musterbriefe"


def template_path(file_name: str) -> Path:
    """Resolve a manifest ``file`` entry to the markdown file on disk."""
    return musterbriefe_dir() / file_name


def read_template(file_name: str) -> str:
    """Read one Musterbrief file; raises :class:`BrainNotFound` if absent."""
    path = template_path(file_name)
    if not path.is_file():
        raise BrainNotFound(f"Musterbrief not found: {path}")
    return path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- derived views


@lru_cache(maxsize=1)
def rules() -> tuple[Rule, ...]:
    """Parse ``regelwerk.md`` into :class:`Rule` objects (R1..R67)."""
    parsed: list[Rule] = []
    for line in regelwerk_text().splitlines():
        match = _RULE_RE.match(line.strip())
        if match:
            parsed.append(Rule(id=f"R{match.group(1)}", text=match.group(2), provenance=match.group(3)))
    return tuple(parsed)


def rule_lines() -> list[str]:
    """The regelwerk rendered as ``R<n>: <rule>`` lines (for prompt embedding)."""
    return [f"{rule.id}: {rule.text}" for rule in rules()]


def anti_pattern_lines() -> list[str]:
    """Yield ``AP-<n>: <title>`` lines parsed from ANTI-PATTERNS.md."""
    lines: list[str] = []
    for line in anti_patterns_text().splitlines():
        match = re.match(r"^###\s+(AP-\d+)\s*—\s*(.+)$", line.strip())
        if match:
            lines.append(f"{match.group(1)}: {match.group(2)}")
    return lines


def brain_version() -> str:
    """README/frontmatter brain version if detectable, else ``unknown``."""
    for line in kern_text().splitlines():
        match = re.match(r"brain_version:\s*(\S+)", line.strip())
        if match:
            return match.group(1)
    return BRAIN_VERSION_FALLBACK


def status() -> dict[str, Any]:
    """A small diagnostics dict (used by the demo and tests)."""
    return {
        "brain_dir": str(brain_root()),
        "brain_version": brain_version(),
        "rules": len(rules()),
        "anti_patterns": len(anti_pattern_lines()),
        "playbooks": len(DOKUMENTTYPEN),
        "templates": len(templates()),
        "musterbriefe_dir": str(musterbriefe_dir()),
    }


def clear_caches() -> None:
    """Drop every cache (tests set ``BRIEFATO_BRAIN_DIR`` between cases)."""
    for func in (
        kern_text,
        regelwerk_text,
        anti_patterns_text,
        stolperfallen_text,
        regeln_aus_praxis_text,
        dokumenttyp_text,
        manifest,
        musterbriefe_dir,
        rules,
        standards_index_text,
        standard_text,
    ):
        func.cache_clear()


__all__ = [
    "BrainError",
    "BrainNotFound",
    "DOKUMENTTYPEN",
    "DOKUMENTTYP_LABELS",
    "Rule",
    "anti_pattern_lines",
    "brain_root",
    "brain_version",
    "clear_caches",
    "dokumenttyp_text",
    "kern_text",
    "manifest",
    "musterbriefe_dir",
    "read_template",
    "regelwerk_text",
    "rule_lines",
    "rules",
    "status",
    "standard_text",
    "standards_index_text",
    "template_path",
    "templates",
]

"""Briefato brain package — the harvested Schreibdienst method, in code.

OWNER: WORKSTREAM-BRAIN-WIRING.

Modules
-------
brain_loader.py     cached loaders for kern / regelwerk / anti-patterns / playbooks / manifest
triage.py           Auftragsart -> Dokumenttyp (kern.md routing table)
retrieval.py        diagnose keyword matching against the 152 Musterbriefe
prompt_assembly.py  system + user prompt built from the brain (plain-text mandate)
rule_checker.py     deterministic R1-R67 + ANTI-PATTERNS enforcement

The brain markdown under ``<repo>/brain`` is an input and is never modified.
"""

from __future__ import annotations

from . import brain_loader, prompt_assembly, retrieval, rule_checker, triage
from .brain_loader import BrainError, BrainNotFound
from .prompt_assembly import PromptBundle, build_prompt
from .retrieval import TemplateHit, retrieve
from .rule_checker import CheckResult, Finding, check
from .triage import DOC_TYPES, TriageDecision, doc_type_options, triage as triage_document

__all__ = [
    "BrainError",
    "BrainNotFound",
    "CheckResult",
    "DOC_TYPES",
    "Finding",
    "PromptBundle",
    "TemplateHit",
    "TriageDecision",
    "brain_loader",
    "build_prompt",
    "check",
    "doc_type_options",
    "prompt_assembly",
    "retrieval",
    "retrieve",
    "rule_checker",
    "triage",
    "triage_document",
]

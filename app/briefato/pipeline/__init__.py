"""Briefato letter-generation pipeline (OWNER: WORKSTREAM-PIPELINE).

Modules
-------
pseudonym.py   patient pseudonymisation (tokenise before every model call, D4)
providers.py   provider abstraction (Mock / OpenAI-compatible, D5)
prompts.py     versioned German prompt engineering
letterhead.py  DOCX letterhead rendering (DIN 5008 oriented)
generate.py    end-to-end orchestration (pseudonymise -> model -> restore -> store, D7)

Frozen API: docs/02-spec-interfaces.md §6.
"""

from __future__ import annotations

from . import fanout, routing, segmenter
from .generate import PipelineGenerationError, generate_letter, render_docx
from .letterhead import render_docx as render_docx  # noqa: F811  (frozen location lives in letterhead)
from .prompts import PROMPT_VERSION, system_prompt, user_prompt
from .providers import (
    LLMProvider,
    LLMResult,
    MockProvider,
    OpenAICompatProvider,
    PipelineError,
    PipelineProviderError,
    get_provider,
)
from .pseudonym import Pseudonymizer

__all__ = [
    "PROMPT_VERSION",
    "LLMProvider",
    "LLMResult",
    "MockProvider",
    "OpenAICompatProvider",
    "PipelineError",
    "PipelineGenerationError",
    "PipelineProviderError",
    "Pseudonymizer",
    "fanout",
    "generate_letter",
    "get_provider",
    "render_docx",
    "routing",
    "segmenter",
    "system_prompt",
    "user_prompt",
]

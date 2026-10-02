"""Letter generation pipeline.

OWNER: WORKSTREAM-PIPELINE. This file is a STUB so the portal can import the frozen interface
before the real implementation lands — replace it entirely.

Frozen signature (docs/02-spec-interfaces.md §6):
    generate_letter(db, *, user, patient, kind, dictation, letterhead, extra="") -> Letter
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

STUB = True


def generate_letter(
    db,
    *,
    user,
    patient,
    kind: str,
    dictation: str,
    letterhead: dict,
    extra: str = "",
) -> Any:  # pragma: no cover - replaced by WORKSTREAM-PIPELINE
    raise NotImplementedError("pipeline stub: WORKSTREAM-PIPELINE has not landed yet")


def render_docx(
    letter_text: str,
    letterhead: dict,
    patient_ctx: dict,
    out_path: Path,
    kind: str,
) -> Path:  # pragma: no cover - replaced by WORKSTREAM-PIPELINE
    raise NotImplementedError("pipeline stub: WORKSTREAM-PIPELINE has not landed yet")

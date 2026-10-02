"""Letter generation orchestration.

OWNER: WORKSTREAM-PIPELINE. Frozen API (docs/02-spec-interfaces.md §6)::

    def generate_letter(db, *, user, patient, kind: str, dictation: str,
                        letterhead: dict, extra: str = "") -> Letter

Flow (decisions D4/D5/D7):

    create Letter(status="generating")
      -> pseudonymise dictation AND patient context (Pseudonymizer)
      -> prompt (prompts.system_prompt / user_prompt)
      -> debug assertion that no raw identifier reached the prompt (env != "prod")
      -> provider.generate
      -> restore tokens
      -> store content_enc (Fernet), status="done", tokens/cost
      -> Generation row (pseudonymised=True)
      -> increment subscription.letters_used (only on success)
      -> audit event

On any failure the letter is marked ``failed`` with a German-safe error string, the
quota is left untouched and a clear :class:`PipelineGenerationError` is raised — a
letter is never left stuck in ``generating``.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy import select

from .. import security
from ..config import get_settings
from ..models import Generation, Letter, Subscription
from .letterhead import render_docx  # re-exported for the frozen generate.py API
from .prompts import KIND_LABELS, system_prompt, user_prompt
from .providers import PipelineError, get_provider
from .pseudonym import Pseudonymizer

logger = logging.getLogger(__name__)

_GENERIC_ERROR = "Die Erzeugung ist fehlgeschlagen. Bitte versuchen Sie es erneut."

# Identifiers that are genuinely patient-specific and must never reach the prompt.
# Weak fields (city, zip) are excluded: they can legitimately coincide with the
# practice's own address, which is part of the letterhead and intentionally sent.
_STRONG_IDENTIFIER_TOKENS = (
    "{{LAST_NAME}}",
    "{{FIRST_NAME}}",
    "{{BIRTH_DATE}}",
    "{{INSURANCE_NUMBER}}",
    "{{STREET}}",
    "{{PHONE}}",
    "{{EMAIL}}",
)


class PipelineGenerationError(PipelineError):
    """Raised when a letter could not be generated (letter row now status='failed')."""


def _format_birth_date(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%d.%m.%Y")
    return str(value).strip()


def _patient_context(patient: Any) -> dict[str, str]:
    if patient is None:
        return {}
    context = {
        "last_name": getattr(patient, "last_name", "") or "",
        "first_name": getattr(patient, "first_name", "") or "",
        "birth_date": _format_birth_date(getattr(patient, "birth_date", None)),
        "sex": getattr(patient, "sex", "") or "",
        "insurance": getattr(patient, "insurance", "") or "",
        "insurance_number": getattr(patient, "insurance_number", "") or "",
        "street": getattr(patient, "street", "") or "",
        "zip": getattr(patient, "zip", "") or "",
        "city": getattr(patient, "city", "") or "",
        "phone": getattr(patient, "phone", "") or "",
        "email": getattr(patient, "email", "") or "",
    }
    return {key: str(value).strip() for key, value in context.items() if str(value).strip()}


def _effective_letterhead(letterhead: dict | None, user: Any) -> dict:
    merged = dict(letterhead or {})
    for key in ("practice_name", "full_name", "street", "zip", "city", "phone", "email", "tax_id"):
        if not str(merged.get(key) or "").strip():
            value = getattr(user, key, "")
            if value:
                merged[key] = value
    return merged


def _error_message(exc: BaseException) -> str:
    """German-safe error string: no patient data, no provider payload, no key."""
    message = _GENERIC_ERROR
    status_code = getattr(exc, "status_code", None)
    if status_code:
        message += f" (Fehlercode {status_code})"
    return message


def _assert_prompt_is_pseudonymised(
    pseudonymizer: Pseudonymizer, prompt: str, settings: Any, *, ignore: str = ""
) -> None:
    """Enforce D4 in code: no raw identifier may appear in the outgoing prompt.

    Values that are also part of the practice's own letterhead (e.g. a practice named
    'Praxis Dr. Anna Beispiel' with a patient called Anna) are legitimately present in the
    prompt and are therefore excluded from the check.

    Guarded to non-production environments so an unforeseen false positive can never
    take down a live request; in dev/staging it fails loudly (AssertionError).
    """
    if getattr(settings, "env", "dev") == "prod":
        return
    haystack = prompt.lower()
    ignore = (ignore or "").lower()
    leaked = [
        value
        for value in pseudonymizer.sensitive_values(_STRONG_IDENTIFIER_TOKENS)
        if len(value) >= 3 and value in haystack and value not in ignore
    ]
    if leaked:
        # Never echo the leaked values themselves.
        raise AssertionError(
            f"pseudonymisation leak: {len(leaked)} raw identifier(s) present in the provider prompt"
        )


def _mark_failed(
    db: Any,
    *,
    letter_id: str,
    user_id: str,
    kind: str,
    exc: BaseException,
    model: str,
) -> None:
    try:
        letter = db.get(Letter, letter_id)
        if letter is None:
            return
        letter.status = "failed"
        letter.error = _error_message(exc)
        db.add(letter)
        # Record the failed attempt for observability; quota is never touched here.
        try:
            db.add(
                Generation(
                    user_id=user_id,
                    letter_id=letter_id,
                    provider=str(getattr(exc, "provider", "") or ""),
                    model=model,
                    tokens_in=0,
                    tokens_out=0,
                    cost_usd=0.0,
                    latency_ms=0,
                    status="error",
                    pseudonymised=True,
                    error=letter.error[:500],
                )
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception("could not record failed Generation row for letter %s", letter_id)
        db.commit()
        try:
            security.audit(
                db,
                event="letter.failed",
                user_id=user_id,
                target_type="letter",
                target_id=letter_id,
                kind=kind,
                error_type=type(exc).__name__,
            )
        except Exception:  # pragma: no cover - audit must not mask the failure
            logger.exception("audit failed for failed letter %s", letter_id)
    except Exception:  # pragma: no cover - last-resort safety net
        db.rollback()
        logger.exception("could not mark letter %s as failed", letter_id)


def generate_letter(
    db,
    *,
    user,
    patient,
    kind: str,
    dictation: str,
    letterhead: dict,
    extra: str = "",
) -> Letter:
    settings = get_settings()

    label = KIND_LABELS.get(kind, KIND_LABELS["sonstiges"])
    patient_name = ""
    if patient is not None:
        patient_name = (
            (getattr(patient, "last_name", "") or "").strip()
            or (getattr(patient, "first_name", "") or "").strip()
        )
    title = f"{label} {patient_name}".strip()[:200] or label

    letter = Letter(
        user_id=user.id,
        patient_id=getattr(patient, "id", None),
        kind=kind,
        status="generating",
        title=title,
        dictation_enc=security.encrypt_field(dictation or ""),
        language=(getattr(user, "ui_lang", None) or settings.ui_lang),
        model=settings.llm_model,
    )
    db.add(letter)
    db.commit()
    db.refresh(letter)

    try:
        pseudonymizer = Pseudonymizer.from_patient(patient)
        masked_dictation = pseudonymizer.mask(dictation or "")
        masked_context = {
            key: pseudonymizer.mask(value) for key, value in _patient_context(patient).items()
        }
        effective_letterhead = _effective_letterhead(letterhead, user)

        system = system_prompt(kind, letter.language)
        user_prompt_text = user_prompt(
            kind, masked_dictation, masked_context, effective_letterhead, extra=extra or ""
        )
        _assert_prompt_is_pseudonymised(
            pseudonymizer,
            f"{system}\n{user_prompt_text}",
            settings,
            ignore=" ".join(str(value) for value in effective_letterhead.values()),
        )

        provider = get_provider(settings)
        result = provider.generate(system, user_prompt_text)
        restored = pseudonymizer.restore(result.text)

        letter.content_enc = security.encrypt_field(restored)
        letter.tokens_in = int(result.tokens_in or 0)
        letter.tokens_out = int(result.tokens_out or 0)
        letter.cost_usd = float(result.cost_usd or 0.0)
        letter.model = result.model or settings.llm_model
        letter.status = "done"
        letter.error = ""
        db.add(letter)

        db.add(
            Generation(
                user_id=user.id,
                letter_id=letter.id,
                provider=result.provider,
                model=letter.model,
                tokens_in=letter.tokens_in,
                tokens_out=letter.tokens_out,
                cost_usd=letter.cost_usd,
                latency_ms=int(result.latency_ms or 0),
                status="ok",
                pseudonymised=True,
                error="",
            )
        )

        subscription = db.scalar(select(Subscription).where(Subscription.user_id == user.id))
        if subscription is not None:
            subscription.letters_used = int(subscription.letters_used or 0) + 1

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("letter generation failed letter_id=%s kind=%s", letter.id, kind)
        _mark_failed(db, letter_id=letter.id, user_id=user.id, kind=kind, exc=exc, model=settings.llm_model)
        raise PipelineGenerationError(_error_message(exc)) from exc

    # Success audit is best-effort: the letter is already committed as done.
    try:
        security.audit(
            db,
            event="letter.generated",
            user_id=user.id,
            target_type="letter",
            target_id=letter.id,
            kind=kind,
            model=letter.model,
            tokens_in=letter.tokens_in,
            tokens_out=letter.tokens_out,
            cost_usd=letter.cost_usd,
            pseudonymised=True,
        )
    except Exception:  # pragma: no cover - audit failure must not fail the letter
        logger.exception("audit failed for letter %s", letter.id)

    return letter


__all__ = ["generate_letter", "render_docx", "PipelineGenerationError"]

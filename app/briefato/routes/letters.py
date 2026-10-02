"""Letters: create drafts, generate via the pipeline, edit, approve, export, delete."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select

from .. import billing
from ..config import get_settings
from ..models import LETTER_KINDS, Generation, Letter, Patient, new_id, utcnow
from ..pipeline import generate as pipeline_generate
from ..security import audit, decrypt_field, encrypt_field
from . import brain_bridge
from .deps import (
    CSRF,
    DB,
    CurrentUser,
    LETTER_KIND_LABELS,
    get_letter_or_404,
    get_patient_or_404,
    get_subscription,
    render,
)

router = APIRouter(prefix="/app/briefe", tags=["briefe"])

DOCX_MEDIA = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

_PIPELINE_GENERATION_ERROR = getattr(pipeline_generate, "PipelineGenerationError", None)
_GENERIC_GENERATE_ERROR = (
    "Der Brief konnte nicht erzeugt werden. Bitte prüfen Sie das Diktat und versuchen Sie es erneut."
)


def _pipeline_error_message(exc: BaseException) -> str:
    """Prefer the pipeline's German-safe message; never surface a raw exception string."""
    if _PIPELINE_GENERATION_ERROR is not None and isinstance(exc, _PIPELINE_GENERATION_ERROR):
        text = str(exc).strip()
        if text:
            return text
    return _GENERIC_GENERATE_ERROR


def _quota(db, user) -> dict:
    try:
        return billing.quota_state(db, user)
    except NotImplementedError:
        sub = get_subscription(db, user)
        return {
            "plan": sub.plan_code,
            "quota": sub.letters_quota,
            "used": sub.letters_used,
            "remaining": max(sub.letters_quota - sub.letters_used, 0),
            "period_end": None,
        }


def _editor_context(db, user, letter: Letter, **extra) -> dict:
    dictation = decrypt_field(letter.dictation_enc)
    content = decrypt_field(letter.content_enc)
    selected_type = brain_bridge.resolve_explicit_type(letter.template_id)
    detection = brain_bridge.detect_type(dictation, selected_type)
    has_text = bool((dictation or "").strip() or (content or "").strip())
    context = {
        "letter": letter,
        "dictation": dictation,
        "content": content,
        "quota": _quota(db, user),
        # Method (brain) view for the editor.
        "doc_types": brain_bridge.available_types(),
        "selected_type": selected_type,
        "detection": detection,
        "used_templates": brain_bridge.search_templates(dictation or content) if has_text else [],
        "rule_check": brain_bridge.check_rules(content, detection["key"], dictation) if content.strip() else None,
        "brain_available": brain_bridge.brain_available(),
        "method_message": brain_bridge.method_message(),
        "custom_rules": str((user.letterhead_json or {}).get("custom_rules", "") or ""),
        "active": "briefe",
        "error": None,
        "generated": False,
    }
    context.update(extra)
    return context


def _merge_fields(letter: Letter, source) -> None:
    """Copy generation output (content, tokens, status) onto the portal's letter row."""
    if source is None:
        return
    for field in (
        "content_enc",
        "model",
        "tokens_in",
        "tokens_out",
        "cost_usd",
        "language",
        "template_id",
        "error",
    ):
        value = getattr(source, field, None)
        if value not in (None, ""):
            setattr(letter, field, value)
    status = getattr(source, "status", None) or "done"
    letter.status = "done" if status in ("generating", "queued") else status


def _letter_ids(db, user) -> set[str]:
    return set(db.scalars(select(Letter.id).where(Letter.user_id == user.id)).all())


def _fold_pipeline_letters(db, user, draft: Letter, before_ids: set[str], source) -> None:
    """The frozen pipeline creates and returns its *own* Letter row. The portal keeps the
    draft the member opened as the canonical record: copy the result onto it, re-point any
    Generation rows and remove the transient duplicate so no ghost letters accumulate.

    The pipeline row is identified by **id difference** against the ids that existed before the
    call — never by a time window, which would also swallow a letter the member created in a
    second tab while the model was running.
    """
    new_ids = _letter_ids(db, user) - before_ids - {draft.id}
    source_id = getattr(source, "id", None)

    # 1. the returned object is the authoritative result — always merge it onto the draft
    if source is not None:
        _merge_fields(draft, source)
    elif len(new_ids) == 1:
        fallback = db.get(Letter, next(iter(new_ids)))
        if fallback is not None and fallback.user_id == user.id:
            _merge_fields(draft, fallback)

    # 2. remove the pipeline's own row, but ONLY if the pipeline really created it during this
    #    call (id difference) — never touch any other letter the member may have created meanwhile
    if source_id is None or source_id not in new_ids:
        return
    stray = db.get(Letter, source_id)
    if stray is None or stray.user_id != user.id:
        return
    for generation in db.scalars(select(Generation).where(Generation.letter_id == stray.id)):
        generation.letter_id = draft.id
    db.flush()
    db.delete(stray)


def _slug(value: str) -> str:
    value = value.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-") or "brief"


# --------------------------------------------------------------------------- list


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
def liste(request: Request, db: DB, user: CurrentUser, q: str | None = None, status: str | None = None):
    stmt = select(Letter).where(Letter.user_id == user.id)
    term = (q or "").strip()
    if term:
        stmt = stmt.where(Letter.title.ilike(f"%{term}%"))
    if status and status in ("draft", "queued", "generating", "done", "failed", "approved"):
        stmt = stmt.where(Letter.status == status)
    letters = db.scalars(stmt.order_by(Letter.created_at.desc())).all()
    return render(
        request,
        "app/briefe/liste.html",
        letters=letters,
        q=term,
        status=status or "",
        active="briefe",
        crumbs=[("Übersicht", "/app"), ("Briefe", None)],
    )


# --------------------------------------------------------------------------- create


@router.get("/neu", include_in_schema=False)
def neu_form(request: Request, db: DB, user: CurrentUser, patient_id: str | None = None):
    patients = db.scalars(
        select(Patient)
        .where(Patient.user_id == user.id, Patient.archived_at.is_(None))
        .order_by(Patient.last_name, Patient.first_name)
    ).all()
    return render(
        request,
        "app/briefe/neu.html",
        patients=patients,
        form={"patient_id": patient_id or "", "kind": "arztbrief", "title": "", "dictation": ""},
        errors={},
        error=None,
        active="briefe",
        crumbs=[("Übersicht", "/app"), ("Briefe", "/app/briefe"), ("Neu", None)],
    )


@router.post("/neu", include_in_schema=False, dependencies=[CSRF])
async def neu_submit(request: Request, db: DB, user: CurrentUser):
    form = await request.form()
    values = {
        "patient_id": str(form.get("patient_id", "")).strip(),
        "kind": str(form.get("kind", "arztbrief")).strip(),
        "title": str(form.get("title", "")).strip(),
        "dictation": str(form.get("dictation", "")).strip(),
    }
    errors: dict[str, str] = {}
    if not values["title"]:
        errors["title"] = "Bitte geben Sie einen Titel an."
    if not values["dictation"]:
        errors["dictation"] = "Bitte diktieren Sie den Inhalt."
    if values["kind"] not in LETTER_KINDS:
        values["kind"] = "arztbrief"
    patient = get_patient_or_404(db, user, values["patient_id"]) if values["patient_id"] else None
    if patient is None and "patient_id" not in errors:
        errors["patient_id"] = "Bitte wählen Sie einen Patienten."

    if errors:
        patients = db.scalars(
            select(Patient)
            .where(Patient.user_id == user.id, Patient.archived_at.is_(None))
            .order_by(Patient.last_name, Patient.first_name)
        ).all()
        return render(
            request,
            "app/briefe/neu.html",
            patients=patients,
            form=values,
            errors=errors,
            error=None,
            active="briefe",
            crumbs=[("Übersicht", "/app"), ("Briefe", "/app/briefe"), ("Neu", None)],
            status_code=400,
        )

    letter = Letter(
        id=new_id(),
        user_id=user.id,
        patient_id=patient.id,
        kind=values["kind"],
        title=values["title"],
        language=user.ui_lang or "de",
        status="draft",
        dictation_enc=encrypt_field(values["dictation"]),
    )
    db.add(letter)
    db.commit()
    audit(db, event="letter.created", user_id=user.id, target_type="letter", target_id=letter.id, request=request)
    return RedirectResponse(f"/app/briefe/{letter.id}?m=brief_angelegt", status_code=303)


# --------------------------------------------------------------------------- detail


@router.get("/{letter_id}", include_in_schema=False)
def detail(request: Request, db: DB, user: CurrentUser, letter_id: str):
    letter = get_letter_or_404(db, user, letter_id)
    return render(
        request,
        "app/briefe/detail.html",
        **_editor_context(db, user, letter),
        crumbs=[
            ("Übersicht", "/app"),
            ("Briefe", "/app/briefe"),
            (letter.title or "Brief", None),
        ],
    )


# --------------------------------------------------------------------------- generate


@router.post("/{letter_id}/erzeugen", include_in_schema=False, dependencies=[CSRF])
async def erzeugen(request: Request, db: DB, user: CurrentUser, letter_id: str):
    letter = get_letter_or_404(db, user, letter_id)
    htmx = request.headers.get("HX-Request") is not None

    if letter.status == "approved":
        return _editor_response(
            request, db, user, letter, htmx=htmx, error="Freigegebene Briefe sind gesperrt.",
            crumbs=[("Übersicht", "/app"), ("Briefe", "/app/briefe"), (letter.title or "Brief", None)],
        )

    form = await request.form()
    dictation = str(form.get("dictation", "")).strip()
    doc_type = brain_bridge.resolve_explicit_type(str(form.get("doc_type", "")))
    if not dictation:
        return _editor_response(
            request, db, user, letter, htmx=htmx, error="Bitte geben Sie zuerst ein Diktat ein.",
            crumbs=[("Übersicht", "/app"), ("Briefe", "/app/briefe"), (letter.title or "Brief", None)],
        )

    quota = _quota(db, user)
    if quota.get("remaining", 0) <= 0:
        return _editor_response(
            request, db, user, letter, htmx=htmx,
            error="Ihr Kontingent ist aufgebraucht. Bitte wählen Sie unter „Abrechnung“ einen Plan, "
                  "um weitere Briefe zu erzeugen.",
            crumbs=[("Übersicht", "/app"), ("Briefe", "/app/briefe"), (letter.title or "Brief", None)],
            status_code=402,
        )

    letter.dictation_enc = encrypt_field(dictation)
    # The explicit document-type choice (or "auto") is persisted on the frozen ``template_id``
    # column; it is written again after folding because the pipeline result carries its own
    # default for that field.
    letter.template_id = doc_type
    db.commit()

    patient = letter.patient
    before_ids = _letter_ids(db, user)
    error = None
    generated = False
    result = None
    try:
        result = pipeline_generate.generate_letter(
            db,
            user=user,
            patient=patient,
            kind=letter.kind,
            dictation=dictation,
            letterhead=user.letterhead_json or {},
        )
    except NotImplementedError:
        error = "Die Brief-Erzeugung ist in dieser Umgebung noch nicht verfügbar."
        audit(db, event="letter.generate_unavailable", user_id=user.id, target_type="letter",
              target_id=letter.id, request=request)
    except Exception as exc:  # noqa: BLE001 - surface a plain German message, log the rest
        error = _pipeline_error_message(exc)
        audit(db, event="letter.generate_failed", user_id=user.id, target_type="letter",
              target_id=letter.id, request=request, error=f"{type(exc).__name__}")

    if error is None:
        generated = True
        letter.error = ""
    # The pipeline keeps its own accounting (quota + audit); the portal only folds the
    # resulting letter row (or the failed one) back onto the member's draft.
    _fold_pipeline_letters(db, user, letter, before_ids, result)
    letter.template_id = doc_type
    if error is not None and letter.status != "failed":
        letter.status = "failed"
        letter.error = error
    db.commit()

    return _editor_response(
        request, db, user, letter, htmx=htmx, error=error, generated=generated,
        crumbs=[("Übersicht", "/app"), ("Briefe", "/app/briefe"), (letter.title or "Brief", None)],
        status_code=502 if error else 200,
    )


def _editor_response(
    request: Request,
    db,
    user,
    letter: Letter,
    *,
    htmx: bool,
    error: str | None = None,
    generated: bool = False,
    status_code: int = 200,
    crumbs=None,
):
    context = _editor_context(db, user, letter, error=error, generated=generated, crumbs=crumbs)
    if htmx:
        return render(request, "app/briefe/_editor.html", status_code=status_code, **context)
    if error:
        return render(request, "app/briefe/detail.html", status_code=status_code, **context)
    return RedirectResponse(f"/app/briefe/{letter.id}?m=brief_erzeugt", status_code=303)


# --------------------------------------------------------------------------- save / approve


@router.post("/{letter_id}/speichern", include_in_schema=False, dependencies=[CSRF])
async def speichern(request: Request, db: DB, user: CurrentUser, letter_id: str):
    letter = get_letter_or_404(db, user, letter_id)
    if letter.status == "approved":
        return RedirectResponse(f"/app/briefe/{letter.id}", status_code=303)
    form = await request.form()
    content = str(form.get("content", ""))
    letter.content_enc = encrypt_field(content) if content.strip() else None
    db.commit()
    audit(db, event="letter.saved", user_id=user.id, target_type="letter", target_id=letter.id, request=request)
    return RedirectResponse(f"/app/briefe/{letter.id}?m=brief_gespeichert", status_code=303)


@router.post("/{letter_id}/freigeben", include_in_schema=False, dependencies=[CSRF])
def freigeben(request: Request, db: DB, user: CurrentUser, letter_id: str):
    letter = get_letter_or_404(db, user, letter_id)
    if letter.status == "approved":
        return RedirectResponse(f"/app/briefe/{letter.id}?m=brief_freigegeben", status_code=303)
    if not decrypt_field(letter.content_enc).strip():
        return RedirectResponse(f"/app/briefe/{letter.id}", status_code=303)
    letter.status = "approved"
    letter.approved_at = utcnow()
    db.commit()
    audit(db, event="letter.approved", user_id=user.id, target_type="letter", target_id=letter.id, request=request)
    return RedirectResponse(f"/app/briefe/{letter.id}?m=brief_freigegeben", status_code=303)


# --------------------------------------------------------------------------- export


@router.get("/{letter_id}/export.docx", include_in_schema=False)
def export_docx(request: Request, db: DB, user: CurrentUser, letter_id: str):
    letter = get_letter_or_404(db, user, letter_id)
    content = decrypt_field(letter.content_enc)
    if not content.strip():
        return RedirectResponse(f"/app/briefe/{letter.id}", status_code=303)

    patient = letter.patient
    patient_ctx = (
        {
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "birth_date": patient.birth_date.isoformat() if patient.birth_date else "",
            "street": patient.street,
            "zip": patient.zip,
            "city": patient.city,
            "insurance": patient.insurance,
            "insurance_number": patient.insurance_number,
        }
        if patient
        else {}
    )
    settings = get_settings()
    out_path = settings.letters_dir / f"brief-{letter.id}.docx"
    try:
        renderer = getattr(pipeline_generate, "render_docx", None)
        if renderer is None:
            from ..pipeline import letterhead as pipeline_letterhead

            renderer = pipeline_letterhead.render_docx
        rendered = renderer(content, user.letterhead_json or {}, patient_ctx, out_path, letter.kind)
    except NotImplementedError:
        return render(
            request,
            "app/briefe/detail.html",
            **_editor_context(db, user, letter, error="Der DOCX-Export ist in dieser Umgebung noch nicht verfügbar."),
            crumbs=[("Übersicht", "/app"), ("Briefe", "/app/briefe"), (letter.title or "Brief", None)],
            status_code=503,
        )
    except Exception as exc:  # noqa: BLE001
        audit(db, event="letter.export_failed", user_id=user.id, target_type="letter",
              target_id=letter.id, request=request, error=f"{type(exc).__name__}: {exc}"[:400])
        return render(
            request,
            "app/briefe/detail.html",
            **_editor_context(db, user, letter, error="Der Export ist fehlgeschlagen. Bitte versuchen Sie es erneut."),
            crumbs=[("Übersicht", "/app"), ("Briefe", "/app/briefe"), (letter.title or "Brief", None)],
            status_code=500,
        )

    path = Path(rendered)
    if not path.is_file():
        return render(
            request,
            "app/briefe/detail.html",
            **_editor_context(db, user, letter, error="Die Exportdatei konnte nicht erstellt werden."),
            crumbs=[("Übersicht", "/app"), ("Briefe", "/app/briefe"), (letter.title or "Brief", None)],
            status_code=500,
        )

    audit(db, event="letter.exported", user_id=user.id, target_type="letter", target_id=letter.id, request=request)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    kind_label = _slug(LETTER_KIND_LABELS.get(letter.kind, letter.kind))
    patient_label = _slug(patient.last_name if patient else "ohne-patient")
    filename = f"{kind_label}-{patient_label}-{stamp}.docx"
    return FileResponse(path=str(path), media_type=DOCX_MEDIA, filename=filename)


# --------------------------------------------------------------------------- delete


@router.post("/{letter_id}/loeschen", include_in_schema=False, dependencies=[CSRF])
def loeschen(request: Request, db: DB, user: CurrentUser, letter_id: str):
    letter = get_letter_or_404(db, user, letter_id)
    db.query(Generation).filter(Generation.letter_id == letter.id, Generation.user_id == user.id).delete(
        synchronize_session=False
    )
    letter_patient_id = letter.patient_id
    db.delete(letter)
    db.commit()
    audit(db, event="letter.deleted", user_id=user.id, target_type="letter", target_id=letter_id, request=request)
    if letter_patient_id:
        return RedirectResponse(f"/app/patienten/{letter_patient_id}?m=brief_geloescht", status_code=303)
    return RedirectResponse("/app/briefe?m=brief_geloescht", status_code=303)

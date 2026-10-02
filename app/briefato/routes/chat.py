"""Chat portal (``/app/chat``) — a conventional chat entry over the frozen no-agent pipeline.

WORKSTREAM-PORTAL. The portal replaces the step-by-step *entry* with a ChatGPT-style
composer while the sequential wizard stays reachable at ``/app/neu`` as the alternative
entry. There is **no agent runtime** in the product: one member turn is at most one
``POST /chat/completions`` (plus the deterministic rule check and at most one repair
retry, both inside the frozen pipeline). No tools, no model memory, no external session —
the thread state lives in *our* database (``chat_threads`` / ``chat_messages``) and this
module assembles the prompt from it.

Turn model
----------
* **New case** — the member types/pastes/dictates free text. The existing
  ``briefato.brain.triage`` decides the document type. When triage is genuinely unsure
  (low confidence on a short, order-only input) the assistant answers with exactly ONE
  short clarifying question plus 2–3 candidate document types as buttons — the only
  "step" left. Otherwise the frozen pipeline generates the letter immediately.
* **Follow-up** — a message in a thread that already has a letter is a refinement of the
  SAME letter (``letter_id`` unchanged): the original dictation is re-generated with the
  accumulated follow-up instructions passed through the pipeline's ``extra`` prompt slot.
  A case therefore stays one document that evolves, never one letter per message.

Privacy
-------
Clinical text is stored Fernet-encrypted (``*_enc`` columns). Pseudonymisation runs
before every model call inside the frozen pipeline (``Pseudonymizer`` + the in-code leak
assertion on the patient-derived payload). Every query is scoped by ``user_id``; a foreign
thread/patient/letter id answers **404**. The thread is persisted, so reopening a case
shows the whole discussion again.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import select

from ..brain import triage as brain_triage
from ..models import (
    ChatMessage,
    ChatThread,
    Letter,
    Patient,
    new_id,
    utcnow,
)
from ..pipeline import generate as pipeline_generate
from ..security import audit, decrypt_field, encrypt_field
from . import brain_bridge
from .deps import (
    CSRF,
    DB,
    LETTER_KIND_LABELS,
    CurrentUser,
    get_patient_or_404,
    get_thread_or_404,
    render,
)
from .letters import _fold_pipeline_letters, _letter_ids, _quota

router = APIRouter(prefix="/app/chat", tags=["chat"])

_GENERIC_GENERATE_ERROR = (
    "Der Text konnte nicht erzeugt werden. Bitte prüfen Sie die Angaben und versuchen Sie es erneut."
)
_PIPELINE_GENERATION_ERROR = getattr(pipeline_generate, "PipelineGenerationError", None)

# Triage asks one clarifying question only when it is *genuinely* unsure: low confidence
# AND a short input that is an order ("Bitte einen Brief") rather than clinical material.
# A long, substantive dictation with no explicit order is the documented default case
# (kern.md K2.1: Rohmaterial ohne Auftrag -> stationärer Arztbrief) and is generated.
_AMBIGUOUS_CONFIDENCE = 0.55
_AMBIGUOUS_MIN_CHARS = 200

# The sentences that rotate above the composer: each names one thing the machine produces.
# German UI copy, no marketing adjectives.
CAPABILITY_LINES: tuple[str, ...] = (
    "Arztbrief aus Ihrer Stichpunktliste.",
    "Attest, knapp und unterschriftsreif.",
    "Befund strukturiert zusammengefasst.",
    "Entlassbrief mit Diagnoseliste am Ende.",
    "OP-Bericht Schritt für Schritt.",
    "Entlassmedikationsplan alt → neu.",
    "Pflegebericht in den Verlauf eingewoben.",
    "Zusammenfassung in drei Sätzen.",
    "Verlegungsbericht mit Verlegungssatz.",
    "Ablehnungsbogen nach Thieme-Standard.",
    "KV-Nachweis für Ihre Weiterbildung.",
)

# Candidate order for the clarifying question: the triaged type first, then the types a
# short order most often actually means.
_CANDIDATE_POOL: tuple[str, ...] = (
    "arztbrief",
    "ambulant",
    "zusammenfassung",
    "operationsbericht",
    "entlassmedikationsplan",
    "befund",
    "attest",
    "ablehnungsbogen",
)

# Brain document type -> the frozen ``letters.kind`` vocabulary (String(20)).
_LETTER_KIND_FOR_DOC_TYPE: dict[str, str] = {
    "arztbrief": "arztbrief",
    "ambulant": "arztbrief",
    "operationsbericht": "arztbrief",
    "zusammenfassung": "arztbrief",
    "pflegebericht": "arztbrief",
    "entlassmedikationsplan": "sonstiges",
    "ablehnungsbogen": "sonstiges",
    "weiterbildung-kv-nachweise": "sonstiges",
    "attest": "attest",
    "befund": "befund",
    "ueberweisung": "ueberweisung",
}

_KNOWN_TYPES = set(brain_triage.DOC_TYPES) | set(LETTER_KIND_LABELS)


# --------------------------------------------------------------------------- helpers


def _doc_type_label(key: str) -> str:
    if key in brain_triage.DOC_TYPE_LABELS:
        return brain_triage.DOC_TYPE_LABELS[key]
    return LETTER_KIND_LABELS.get(key, key or "Dokument")


def _letter_kind(doc_type: str) -> str:
    return _LETTER_KIND_FOR_DOC_TYPE.get(doc_type, "sonstiges")


def _resolve_choice(raw: str | None) -> str:
    """Map a submitted document-type value to a known key, or ``""``."""
    value = (raw or "").strip()
    return value if value in _KNOWN_TYPES else ""


def _needs_clarification(decision, text: str) -> bool:
    if decision.confidence >= _AMBIGUOUS_CONFIDENCE:
        return False
    return len((text or "").strip()) < _AMBIGUOUS_MIN_CHARS


def _candidates(decision) -> list[dict[str, str]]:
    out: list[str] = [decision.doc_type]
    for key in _CANDIDATE_POOL:
        if len(out) >= 3:
            break
        if key and key not in out:
            out.append(key)
    return [{"value": key, "label": _doc_type_label(key)} for key in out[:3]]


def _doc_type_choices() -> list[dict[str, str]]:
    """Override list for 'Weitere Optionen': the brain types plus the legacy kinds."""
    choices = list(brain_bridge.available_types())
    known = {entry["key"] for entry in choices}
    for key in ("attest", "befund", "ueberweisung"):
        if key not in known:
            choices.append({"key": key, "label": LETTER_KIND_LABELS.get(key, key)})
    return choices


def _title(doc_type: str, text: str, patient: Patient | None) -> str:
    label = _doc_type_label(doc_type)
    name = ""
    if patient is not None:
        name = (patient.last_name or patient.first_name or "").strip()
    title = f"{label} {name}".strip()[:200]
    return title or label


def _default_patient(db, user) -> Patient | None:
    return db.scalar(
        select(Patient)
        .where(Patient.user_id == user.id, Patient.archived_at.is_(None))
        .order_by(Patient.created_at.desc())
    )


def _resolve_patient(db, user, raw: str, thread: ChatThread | None) -> Patient | None:
    """Explicit selection wins; else the thread's patient; else the most recent one.

    A foreign id is a 404 (``get_patient_or_404``) — never a silent fallback.
    """
    if raw:
        return get_patient_or_404(db, user, raw)
    if thread is not None and thread.patient_id:
        patient = db.get(Patient, thread.patient_id)
        if patient is not None and patient.user_id == user.id:
            return patient
    return _default_patient(db, user)


def _add_message(db, thread: ChatThread, user, *, role: str, kind: str, content: str,
                 meta: dict | None = None) -> ChatMessage:
    message = ChatMessage(
        id=new_id(),
        thread_id=thread.id,
        user_id=user.id,
        role=role,
        kind=kind,
        content_enc=encrypt_field(content or ""),
        meta_json=meta or {},
    )
    db.add(message)
    db.commit()
    return message


def _serialise_messages(thread: ChatThread | None) -> list[dict]:
    if thread is None:
        return []
    out: list[dict] = []
    for message in thread.messages:
        out.append(
            {
                "id": message.id,
                "role": message.role,
                "kind": message.kind,
                "content": decrypt_field(message.content_enc),
                "meta": dict(message.meta_json or {}),
                "created_at": message.created_at,
            }
        )
    return out


def _pipeline_error_message(exc: BaseException) -> str:
    if _PIPELINE_GENERATION_ERROR is not None and isinstance(exc, _PIPELINE_GENERATION_ERROR):
        text = str(exc).strip()
        if text:
            return text
    return _GENERIC_GENERATE_ERROR


def _templates(last_check, dictation: str) -> list[dict]:
    entries = last_check.get("templates") if isinstance(last_check, dict) else None
    if entries:
        out: list[dict] = []
        for entry in entries[:5]:
            file_name = str(entry.get("file") or "")
            meta = brain_bridge.template_entry(file_name) or {}
            out.append(
                {
                    "file": file_name,
                    "title": meta.get("title", file_name),
                    "score": entry.get("score"),
                }
            )
        return out
    return brain_bridge.search_templates(dictation)[:5]


def _letter_meta(result, letter: Letter, content: str, doc_type: str, dictation: str) -> dict:
    """Non-patient metadata for the assistant letter message (safe to store unencrypted)."""
    last_check = getattr(result, "last_check", None) if result is not None else None
    raw_findings: list = []
    if isinstance(last_check, dict):
        for check in last_check.get("checks") or []:
            raw_findings.extend(check.get("findings") or [])
    if not raw_findings and content.strip():
        bridge = brain_bridge.check_rules(content, doc_type, dictation)
        raw_findings = [
            {
                "rule_id": finding.get("rule"),
                "severity": finding.get("severity") or "soft",
                "message": finding.get("message"),
            }
            for finding in bridge.get("findings", [])
        ]
    findings = [
        {
            "rule_id": str(finding.get("rule_id") or finding.get("rule") or "R"),
            "severity": str(finding.get("severity") or ""),
            "message": str(finding.get("message") or ""),
        }
        for finding in raw_findings
    ]
    hard = [finding for finding in findings if finding["severity"] == "hard"]
    soft = [finding for finding in findings if finding["severity"] != "hard"]
    referenz = [finding for finding in findings if finding["rule_id"] == "R-REFERENZ"]
    return {
        "letter_id": letter.id,
        "doc_type": doc_type,
        "doc_type_label": _doc_type_label(doc_type),
        "hard_count": len(hard),
        "soft_count": len(soft),
        "findings": (hard + soft)[:12],
        "referenz_notes": referenz[:8],
        "templates": _templates(last_check, dictation),
        "model": letter.model,
        "tokens_in": letter.tokens_in,
        "tokens_out": letter.tokens_out,
        "cost_usd": letter.cost_usd,
        "retried": bool(last_check.get("retried")) if isinstance(last_check, dict) else False,
    }


# --------------------------------------------------------------------------- rendering


def _chat_response(
    request: Request,
    db,
    user,
    thread: ChatThread | None,
    *,
    notice: str | None = None,
    error: str | None = None,
    status_code: int = 200,
    selected_patient_id: str | None = None,
):
    patients = db.scalars(
        select(Patient)
        .where(Patient.user_id == user.id, Patient.archived_at.is_(None))
        .order_by(Patient.created_at.desc())
    ).all()
    recent_threads = db.scalars(
        select(ChatThread)
        .where(ChatThread.user_id == user.id)
        .order_by(ChatThread.updated_at.desc())
        .limit(8)
    ).all()
    selected = (
        selected_patient_id
        or (thread.patient_id if thread is not None else None)
        or (patients[0].id if patients else "")
    )
    messages = _serialise_messages(thread)
    return render(
        request,
        "app/chat.html",
        thread=thread,
        messages=messages,
        patients=patients,
        selected_patient_id=selected or "",
        capability_lines=list(CAPABILITY_LINES),
        doc_type_choices=_doc_type_choices(),
        recent_threads=recent_threads,
        notice=notice,
        error=error,
        quota=_quota(db, user),
        active="chat",
        crumbs=[("Übersicht", "/app"), ("Neuer Brief", None)],
        status_code=status_code,
    )


# --------------------------------------------------------------------------- generation


def _generate_and_reply(
    request: Request,
    db,
    user,
    thread: ChatThread,
    letter: Letter,
    patient: Patient | None,
    doc_type: str,
    dictation: str,
    *,
    extra: str = "",
):
    """Run the frozen pipeline once and append the assistant letter/error message."""
    before_ids = _letter_ids(db, user)
    result = None
    error: str | None = None
    try:
        result = pipeline_generate.generate_letter(
            db,
            user=user,
            patient=patient,
            kind=doc_type,
            dictation=dictation,
            letterhead=user.letterhead_json or {},
            extra=extra,
        )
    except NotImplementedError:
        error = "Die Brief-Erzeugung ist in dieser Umgebung noch nicht verfügbar."
        audit(db, event="letter.generate_unavailable", user_id=user.id, target_type="letter",
              target_id=letter.id, request=request)
    except Exception as exc:  # noqa: BLE001 - surface a plain German message, log the rest
        error = _pipeline_error_message(exc)
        audit(db, event="letter.generate_failed", user_id=user.id, target_type="letter",
              target_id=letter.id, request=request, error=f"{type(exc).__name__}")

    _fold_pipeline_letters(db, user, letter, before_ids, result)
    letter.template_id = doc_type
    if error is not None and letter.status != "failed":
        letter.status = "failed"
        letter.error = error
    elif error is None:
        letter.error = ""
    db.commit()

    content = decrypt_field(letter.content_enc)
    if error is not None:
        _add_message(db, thread, user, role="assistant", kind="error", content=error,
                     meta={"letter_id": letter.id})
    else:
        _add_message(db, thread, user, role="assistant", kind="letter", content=content,
                     meta=_letter_meta(result, letter, content, doc_type, dictation))

    thread.updated_at = utcnow()
    db.commit()
    return _chat_response(request, db, user, thread, notice=None if error else "Text erzeugt.")


def _new_letter(
    request: Request, db, user, thread: ChatThread, patient: Patient | None,
    doc_type: str, dictation: str,
) -> Letter:
    letter = Letter(
        id=new_id(),
        user_id=user.id,
        patient_id=patient.id if patient is not None else None,
        kind=_letter_kind(doc_type),
        status="draft",
        title=_title(doc_type, dictation, patient),
        language=user.ui_lang or "de",
        template_id=doc_type,
        dictation_enc=encrypt_field(dictation),
    )
    db.add(letter)
    thread.letter_id = letter.id
    thread.doc_type = doc_type
    thread.title = letter.title
    thread.status = "active"
    db.commit()
    audit(db, event="letter.created", user_id=user.id, target_type="letter",
          target_id=letter.id, request=request, chat=True)
    return letter


def _instructions(db, thread: ChatThread) -> str:
    rows = db.scalars(
        select(ChatMessage)
        .where(
            ChatMessage.thread_id == thread.id,
            ChatMessage.user_id == thread.user_id,
            ChatMessage.role == "user",
            ChatMessage.kind == "followup",
        )
        .order_by(ChatMessage.created_at, ChatMessage.id)
    ).all()
    texts = [decrypt_field(row.content_enc).strip() for row in rows]
    texts = [text for text in texts if text]
    if not texts:
        return ""
    return (
        "Änderungswünsche am selben Dokument (chronologisch, der letzte gilt):\n"
        + "\n".join(f"- {text}" for text in texts)
    )


# --------------------------------------------------------------------------- routes


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
def chat_page(request: Request, db: DB, user: CurrentUser, thread: str | None = None,
              patient_id: str | None = None):
    if thread:
        current = get_thread_or_404(db, user, thread)
        return _chat_response(request, db, user, current)
    return _chat_response(request, db, user, None, selected_patient_id=patient_id)


@router.post("", include_in_schema=False, dependencies=[CSRF])
@router.post("/", include_in_schema=False, dependencies=[CSRF])
async def chat_turn(request: Request, db: DB, user: CurrentUser):
    form = await request.form()
    message = str(form.get("message") or "").strip()
    thread_id = str(form.get("thread_id") or "").strip()
    patient_raw = str(form.get("patient_id") or "").strip()
    override = _resolve_choice(str(form.get("doc_type") or ""))

    current = get_thread_or_404(db, user, thread_id) if thread_id else None

    if not message:
        return _chat_response(
            request, db, user, current,
            error="Bitte geben Sie ein Diktat oder einen Auftrag ein.", status_code=400,
        )

    patient = _resolve_patient(db, user, patient_raw, current)

    # Follow-up: the thread already carries a letter -> refine the SAME document.
    if current is not None and current.letter_id:
        return _followup_turn(request, db, user, current, message, patient)

    return _new_turn(request, db, user, current, message, patient, override)


def _new_turn(request: Request, db, user, current: ChatThread | None, message: str,
              patient: Patient | None, override: str):
    thread = current
    if thread is None:
        thread = ChatThread(
            id=new_id(),
            user_id=user.id,
            patient_id=patient.id if patient is not None else None,
            status="open",
        )
        db.add(thread)
        db.commit()
        audit(db, event="chat.case_opened", user_id=user.id, target_type="chat_thread",
              target_id=thread.id, request=request)
    elif patient is not None and thread.patient_id != patient.id:
        thread.patient_id = patient.id
        db.commit()

    _add_message(db, thread, user, role="user", kind="dictation", content=message)

    if override:
        decision = brain_triage.triage(message, explicit=override)
        doc_type = override
    else:
        decision = brain_triage.triage(message)
        if _needs_clarification(decision, message):
            thread.doc_type = decision.doc_type
            thread.status = "question"
            thread.title = _title(decision.doc_type, message, patient)
            db.commit()
            _add_message(
                db, thread, user,
                role="assistant", kind="question",
                content="Welche Dokumentart soll es sein?",
                meta={"candidates": _candidates(decision), "reason": decision.reason},
            )
            audit(db, event="chat.clarification_asked", user_id=user.id,
                  target_type="chat_thread", target_id=thread.id, request=request,
                  doc_type=decision.doc_type)
            return _chat_response(request, db, user, thread)
        doc_type = decision.doc_type

    letter = _new_letter(request, db, user, thread, patient, doc_type, message)
    audit(db, event="chat.turn", user_id=user.id, target_type="chat_thread",
          target_id=thread.id, request=request, doc_type=doc_type, turn="new")
    return _generate_and_reply(request, db, user, thread, letter, patient, doc_type, message)


def _followup_turn(request: Request, db, user, thread: ChatThread, message: str,
                   patient: Patient | None):
    letter = db.get(Letter, thread.letter_id)
    if letter is None or letter.user_id != user.id:
        return _chat_response(
            request, db, user, thread,
            error="Das Dokument zu diesem Fall wurde nicht gefunden.", status_code=404,
        )

    _add_message(db, thread, user, role="user", kind="followup", content=message)
    if patient is not None and thread.patient_id != patient.id:
        thread.patient_id = patient.id
        db.commit()

    doc_type = thread.doc_type or _resolve_choice(letter.template_id) or "arztbrief"
    dictation = decrypt_field(letter.dictation_enc)
    audit(db, event="chat.turn", user_id=user.id, target_type="chat_thread",
          target_id=thread.id, request=request, doc_type=doc_type, turn="followup")
    return _generate_and_reply(
        request, db, user, thread, letter, patient or letter.patient, doc_type, dictation,
        extra=_instructions(db, thread),
    )


@router.post("/wahl", include_in_schema=False, dependencies=[CSRF])
async def chat_choice(request: Request, db: DB, user: CurrentUser):
    """Answer to the single clarifying question: create the letter for the chosen type."""
    form = await request.form()
    thread = get_thread_or_404(db, user, str(form.get("thread_id") or "").strip())
    choice = _resolve_choice(str(form.get("doc_type") or ""))
    if not choice:
        return _chat_response(
            request, db, user, thread,
            error="Bitte wählen Sie eine gültige Dokumentart.", status_code=400,
        )

    if thread.letter_id:
        # Already generated (e.g. double submit) — show the existing case, never duplicate.
        return _chat_response(request, db, user, thread)

    patient = _resolve_patient(db, user, str(form.get("patient_id") or "").strip(), thread)
    _add_message(db, thread, user, role="user", kind="choice",
                 content=_doc_type_label(choice), meta={"doc_type": choice})

    first = db.scalar(
        select(ChatMessage)
        .where(
            ChatMessage.thread_id == thread.id,
            ChatMessage.user_id == user.id,
            ChatMessage.role == "user",
        )
        .order_by(ChatMessage.created_at, ChatMessage.id)
    )
    dictation = decrypt_field(first.content_enc) if first is not None else ""

    thread.doc_type = choice
    if patient is not None:
        thread.patient_id = patient.id
    db.commit()

    letter = _new_letter(request, db, user, thread, patient, choice, dictation or "Dokument")
    audit(db, event="chat.turn", user_id=user.id, target_type="chat_thread",
          target_id=thread.id, request=request, doc_type=choice, turn="choice")
    return _generate_and_reply(request, db, user, thread, letter, patient, choice,
                               dictation or "Dokument")


__all__ = ["CAPABILITY_LINES", "router"]

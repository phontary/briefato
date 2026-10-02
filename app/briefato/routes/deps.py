"""Shared portal plumbing: template environment, CSRF guard, tenant-scoped getters.

Everything here is WORKSTREAM-PORTAL. It imports the frozen foundation
(``config``, ``db``, ``models``, ``security``) and never edits it.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import PLAN_CATALOG, get_settings
from ..db import get_db
from ..models import ChatThread, Letter, Patient, Subscription, User, utcnow
from ..security import NotAuthenticated, check_csrf, current_user

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

LETTER_KIND_LABELS = {
    "arztbrief": "Arztbrief",
    "attest": "Attest",
    "befund": "Befund",
    "ueberweisung": "Überweisung",
    "sonstiges": "Sonstiges",
}

LETTER_STATUS_LABELS = {
    "draft": "Entwurf",
    "queued": "In Warteschlange",
    "generating": "Wird erzeugt",
    "done": "Erzeugt",
    "failed": "Fehlgeschlagen",
    "approved": "Freigegeben",
}

# Flash codes are short so they survive a redirect without stuffing prose in the URL.
MESSAGES: dict[str, tuple[str, str]] = {
    "patient_angelegt": ("ok", "Der Patient wurde angelegt."),
    "patient_gespeichert": ("ok", "Die Patientendaten wurden gespeichert."),
    "patient_archiviert": ("ok", "Der Patient wurde archiviert."),
    "brief_angelegt": ("ok", "Der Entwurf wurde angelegt."),
    "brief_gespeichert": ("ok", "Der Text wurde gespeichert."),
    "brief_freigegeben": ("ok", "Der Brief wurde freigegeben und ist jetzt gesperrt."),
    "brief_geloescht": ("ok", "Der Brief wurde gelöscht."),
    "regeln_gespeichert": ("ok", "Ihre Regeln wurden gespeichert."),
    "vorschlag_gesendet": ("ok", "Ihr Vorlagen-Vorschlag wurde gesendet und wird geprüft."),
    "vorschlag_ungueltig": ("error", "Bitte geben Sie eine Diagnose für den Vorschlag an."),
    "vorschlag_genehmigt": ("ok", "Der Vorschlag wurde angenommen."),
    "vorschlag_abgelehnt": ("info", "Der Vorschlag wurde abgelehnt."),
    "profil_gespeichert": ("ok", "Ihre Angaben wurden gespeichert."),
    "briefkopf_gespeichert": ("ok", "Der Briefkopf wurde gespeichert."),
    "konto_loeschung": ("ok",
        "Die Löschung Ihres Kontos wurde vorgemerkt. Sie wurden abgemeldet."),
    "passwort_neutral": ("ok",
        "Wenn ein Konto mit dieser Adresse existiert, erhalten Sie eine E-Mail zum "
        "Zurücksetzen. In der aktuellen Version wird noch kein E-Mail-Versand ausgelöst."),
    "passwort_geaendert": ("ok", "Ihr Passwort wurde geändert. Bitte melden Sie sich an."),
    "willkommen": ("ok", "Willkommen bei Briefato. Ihr Konto ist eingerichtet."),
    "abgemeldet": ("ok", "Sie wurden abgemeldet."),
    "billing_erfolg": ("ok", "Ihr Plan wurde aktualisiert."),
    "billing_abgebrochen": ("info", "Der Vorgang wurde abgebrochen."),
    "billing_unavailable": ("error",
        "Die Abrechnung ist noch nicht aktiviert. Bitte wenden Sie sich an den Support."),
}

SESSION_GENERIC_ERROR = "E-Mail-Adresse oder Passwort ist nicht korrekt."


def _fmt_date(value: object) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    return str(value)


def _fmt_datetime(value: object) -> str:
    if not isinstance(value, datetime):
        return _fmt_date(value)
    return value.strftime("%d.%m.%Y, %H:%M")


def _fmt_eur(value: object) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _doc_type_label(value: object) -> str:
    """Human label for a stored brain document type (``letters.template_id``), else "".

    Lets the lists show the real document type (OP-Bericht, Entlassmedikationsplan, …)
    even though the frozen ``letters.kind`` column only knows the legacy kinds.
    """
    raw = str(value or "").strip()
    if not raw or raw == "standard":
        return ""
    try:
        from . import brain_bridge

        if raw in {entry["key"] for entry in brain_bridge.available_types()}:
            return brain_bridge.type_label(raw)
    except Exception:  # noqa: BLE001 - a broken brain must never break a list page
        return ""
    return ""


templates.env.globals.update(
    LETTER_KIND_LABELS=LETTER_KIND_LABELS,
    LETTER_STATUS_LABELS=LETTER_STATUS_LABELS,
    MESSAGES=MESSAGES,
    PLAN_CATALOG=PLAN_CATALOG,
)
templates.env.globals["doc_type_label"] = _doc_type_label
templates.env.filters.update(
    fmt_date=_fmt_date,
    fmt_datetime=_fmt_datetime,
    fmt_eur=_fmt_eur,
)


# --------------------------------------------------------------------------- rendering


def render(request: Request, template: str, *, status_code: int = 200, **context: object):
    """Render a template with the shared portal context (CSRF, settings, user)."""
    message = None
    code = request.query_params.get("m")
    if code and code in MESSAGES:
        kind, text = MESSAGES[code]
        message = {"kind": kind, "text": text}
    base = {
        "request": request,
        "settings": get_settings(),
        "csrf_token": getattr(request.state, "csrf_token", ""),
        "current_user": getattr(request.state, "current_user", None),
        "flash": message,
        "now": utcnow(),
    }
    base.update(context)
    return templates.TemplateResponse(request, template, base, status_code=status_code)


def toast_context(kind: str, text: str) -> dict:
    return {"flash": {"kind": kind, "text": text}}


# --------------------------------------------------------------------------- auth deps


def optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user = current_user(request, db)
    request.state.current_user = user
    return user


def require_auth(request: Request, db: Session = Depends(get_db)) -> User:
    user = current_user(request, db)
    if user is None:
        raise NotAuthenticated
    request.state.current_user = user
    return user


DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(require_auth)]
MaybeUser = Annotated[User | None, Depends(optional_user)]


# --------------------------------------------------------------------------- CSRF


async def verify_csrf(request: Request) -> None:
    """Double-submit CSRF guard for every state-changing portal request."""
    token = request.headers.get("X-CSRF-Token")
    if not token:
        try:
            form = await request.form()
            token = form.get("csrf_token")
        except Exception:  # noqa: BLE001 - malformed body is simply an invalid token
            token = None
    if not check_csrf(request, token if isinstance(token, str) else None):
        raise HTTPException(status_code=403, detail="CSRF-Prüfung fehlgeschlagen.")


CSRF = Depends(verify_csrf)


# --------------------------------------------------------------------------- tenant-scoped getters


def get_patient_or_404(db: Session, user: User, patient_id: str | None) -> Patient:
    if not patient_id:
        raise HTTPException(status_code=404, detail="Patient nicht gefunden.")
    patient = db.scalar(
        select(Patient).where(Patient.id == patient_id, Patient.user_id == user.id)
    )
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient nicht gefunden.")
    return patient


def get_letter_or_404(db: Session, user: User, letter_id: str | None) -> Letter:
    if not letter_id:
        raise HTTPException(status_code=404, detail="Brief nicht gefunden.")
    letter = db.scalar(
        select(Letter).where(Letter.id == letter_id, Letter.user_id == user.id)
    )
    if letter is None:
        raise HTTPException(status_code=404, detail="Brief nicht gefunden.")
    return letter


def get_thread_or_404(db: Session, user: User, thread_id: str | None) -> ChatThread:
    """A chat thread owned by the session user, or 404 — never a foreign thread."""
    if not thread_id:
        raise HTTPException(status_code=404, detail="Fall nicht gefunden.")
    thread = db.scalar(
        select(ChatThread).where(ChatThread.id == thread_id, ChatThread.user_id == user.id)
    )
    if thread is None:
        raise HTTPException(status_code=404, detail="Fall nicht gefunden.")
    return thread


# --------------------------------------------------------------------------- account helpers


def get_subscription(db: Session, user: User) -> Subscription:
    sub = db.scalar(select(Subscription).where(Subscription.user_id == user.id))
    if sub is None:
        sub = Subscription(
            user_id=user.id,
            plan_code="free",
            letters_quota=get_settings().quota_default_letters,
        )
        db.add(sub)
        db.commit()
    return sub

__all__ = [
    "DB",
    "CSRF",
    "CurrentUser",
    "MaybeUser",
    "LETTER_KIND_LABELS",
    "LETTER_STATUS_LABELS",
    "MESSAGES",
    "SESSION_GENERIC_ERROR",
    "STATIC_DIR",
    "TEMPLATES_DIR",
    "get_letter_or_404",
    "get_patient_or_404",
    "get_subscription",
    "get_thread_or_404",
    "optional_user",
    "render",
    "require_auth",
    "toast_context",
    "templates",
    "verify_csrf",
]

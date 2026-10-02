"""Authentication routes: register, login, logout, password flows."""

from __future__ import annotations

import re
from datetime import timedelta

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from ..config import PLAN_CATALOG, get_settings
from ..models import AuditEvent, Subscription, User, utcnow
from ..security import (
    SESSION_COOKIE,
    audit,
    hash_password,
    login_user,
    logout_user,
    verify_password,
)
from .deps import CSRF, DB, SESSION_GENERIC_ERROR, MaybeUser, render

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RESET_SALT = "briefato-password-reset"


def _reset_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt=_RESET_SALT)


def _safe_next(value: str | None, default: str = "/app") -> str:
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return default


def _session_response(raw_token: str, target: str = "/app") -> RedirectResponse:
    settings = get_settings()
    response = RedirectResponse(url=target, status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        raw_token,
        httponly=True,
        samesite="lax",
        secure=settings.is_prod,
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
    return response


def _recent_failures(db, email: str, ip: str) -> int:
    settings = get_settings()
    since = utcnow() - timedelta(minutes=settings.login_window_minutes)
    rows = db.scalars(
        select(AuditEvent).where(
            AuditEvent.event == "auth.login_failed", AuditEvent.created_at >= since
        )
    ).all()
    return sum(
        1
        for row in rows
        if (row.meta_json or {}).get("email") == email or (ip and row.ip == ip)
    )


# --------------------------------------------------------------------------- register


@router.get("/registrieren", include_in_schema=False)
def registrieren_form(request: Request, user: MaybeUser):
    if user is not None:
        return RedirectResponse("/app", status_code=303)
    return render(request, "auth/registrieren.html", form={}, errors={})


@router.post("/registrieren", include_in_schema=False, dependencies=[CSRF])
async def registrieren_submit(
    request: Request,
    db: DB,
    user: MaybeUser,
    full_name: str = Form(""),
    practice_name: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
):
    if user is not None:
        return RedirectResponse("/app", status_code=303)

    form = {
        "full_name": full_name.strip(),
        "practice_name": practice_name.strip(),
        "email": email.strip().lower(),
    }
    errors: dict[str, str] = {}
    if len(form["full_name"]) < 2:
        errors["full_name"] = "Bitte geben Sie Ihren Namen an."
    if not _EMAIL_RE.match(form["email"]):
        errors["email"] = "Bitte geben Sie eine gültige E-Mail-Adresse an."
    elif db.scalar(select(User).where(User.email == form["email"])) is not None:
        errors["email"] = "Diese E-Mail-Adresse ist bereits registriert. Melden Sie sich an."
    if len(password) < 8:
        errors["password"] = "Das Passwort muss mindestens 8 Zeichen lang sein."

    if errors:
        return render(
            request, "auth/registrieren.html", form=form, errors=errors, status_code=400
        )

    account = User(
        email=form["email"],
        password_hash=hash_password(password),
        full_name=form["full_name"],
        practice_name=form["practice_name"],
    )
    db.add(account)
    db.flush()
    db.add(
        Subscription(
            user_id=account.id,
            plan_code="free",
            letters_quota=PLAN_CATALOG["free"]["letters"],
        )
    )
    db.commit()

    audit(db, event="auth.registered", user_id=account.id, request=request, email=account.email)
    raw = login_user(db, account, request)
    return _session_response(raw, "/app?m=" + "willkommen")


# --------------------------------------------------------------------------- login


@router.get("/anmelden", include_in_schema=False)
def anmelden_form(request: Request, user: MaybeUser, next: str | None = None):
    if user is not None:
        return RedirectResponse("/app", status_code=303)
    return render(request, "auth/anmelden.html", error=None, email="", next_url=_safe_next(next))


@router.post("/anmelden", include_in_schema=False, dependencies=[CSRF])
async def anmelden_submit(
    request: Request,
    db: DB,
    user: MaybeUser,
    email: str = Form(""),
    password: str = Form(""),
    next: str = Form(""),
):
    if user is not None:
        return RedirectResponse("/app", status_code=303)

    email = email.strip().lower()
    ip = request.client.host if request.client else ""
    settings = get_settings()
    target = _safe_next(next)

    if _recent_failures(db, email, ip) >= settings.login_max_attempts:
        audit(db, event="auth.login_throttled", request=request, email=email)
        return render(
            request,
            "auth/anmelden.html",
            error=(
                "Zu viele Fehlversuche. Bitte warten Sie "
                f"{settings.login_window_minutes} Minuten und versuchen Sie es erneut."
            ),
            email=email,
            next_url=target,
            status_code=429,
        )

    account = db.scalar(select(User).where(User.email == email))
    if account is None or not account.is_active or not verify_password(password, account.password_hash):
        audit(db, event="auth.login_failed", request=request, email=email)
        return render(
            request,
            "auth/anmelden.html",
            error=SESSION_GENERIC_ERROR,
            email=email,
            next_url=target,
            status_code=401,
        )

    raw = login_user(db, account, request)
    return _session_response(raw, target)


# --------------------------------------------------------------------------- logout


@router.post("/abmelden", include_in_schema=False, dependencies=[CSRF])
def abmelden(request: Request, db: DB):
    logout_user(db, request.cookies.get(SESSION_COOKIE))
    response = RedirectResponse("/?m=abgemeldet", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


# --------------------------------------------------------------------------- password


@router.get("/passwort-vergessen", include_in_schema=False)
def passwort_vergessen_form(request: Request):
    return render(request, "auth/passwort_vergessen.html", sent=False, email="")


@router.post("/passwort-vergessen", include_in_schema=False, dependencies=[CSRF])
async def passwort_vergessen_submit(
    request: Request, db: DB, email: str = Form("")
):
    email = email.strip().lower()
    # No e-mail delivery yet: record the request and always answer neutrally.
    audit(db, event="auth.password_reset_requested", request=request, email=email)
    # The token is generated for a future mail path only; it is stored in the audit
    # meta for operators, never claimed to have been sent to the member.
    token = None
    account = db.scalar(select(User).where(User.email == email)) if email else None
    if account is not None:
        token = _reset_serializer().dumps(account.id)
        audit(
            db,
            event="auth.password_reset_token_created",
            user_id=account.id,
            request=request,
            token_len=len(token),
        )
    return render(request, "auth/passwort_vergessen.html", sent=True, email=email)


@router.get("/passwort-zuruecksetzen", include_in_schema=False)
def passwort_zuruecksetzen_form(request: Request, token: str | None = None):
    return render(
        request, "auth/passwort_zuruecksetzen.html", token=token or "", email="", error=None
    )


@router.post("/passwort-zuruecksetzen", include_in_schema=False, dependencies=[CSRF])
async def passwort_zuruecksetzen_submit(
    request: Request,
    db: DB,
    token: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
):
    settings = get_settings()
    email = email.strip().lower()
    error = None
    try:
        user_id = _reset_serializer().loads(
            token, max_age=settings.session_ttl_hours * 3600
        )
    except (BadSignature, SignatureExpired):
        user_id = None
    except Exception:  # noqa: BLE001 - any malformed token is simply invalid
        user_id = None

    account = db.get(User, user_id) if user_id else None
    if account is None or (email and account.email != email):
        error = "Der Link ist ungültig oder abgelaufen. Fordern Sie einen neuen Link an."
    elif len(password) < 8:
        error = "Das Passwort muss mindestens 8 Zeichen lang sein."

    if error:
        return render(
            request,
            "auth/passwort_zuruecksetzen.html",
            token=token,
            email=email,
            error=error,
            status_code=400,
        )

    account.password_hash = hash_password(password)
    db.commit()
    audit(db, event="auth.password_reset", user_id=account.id, request=request)
    return RedirectResponse("/anmelden?m=passwort_geaendert", status_code=303)

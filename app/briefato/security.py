"""Auth, session, field-encryption and CSRF helpers. Frozen interface — see docs/02-spec-interfaces.md."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError, VerificationError
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Request
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import AuditEvent, AuthSession, User, new_id, utcnow

SESSION_COOKIE = "briefato_session"
CSRF_COOKIE = "briefato_csrf"

_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)


class NotAuthenticated(Exception):
    """Raised by require_user when there is no valid session."""


# --------------------------------------------------------------------------- passwords


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        _hasher.verify(password_hash, password)
        return True
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# --------------------------------------------------------------------------- tokens


def new_session_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_csrf_token() -> str:
    return URLSafeTimedSerializer(get_settings().secret_key, salt="briefato-csrf").dumps(secrets.token_hex(16))


def check_csrf(request: Request, form_token: str | None) -> bool:
    cookie = request.cookies.get(CSRF_COOKIE, "")
    if not cookie or not form_token:
        return False
    if not hmac.compare_digest(cookie, form_token):
        return False
    try:
        URLSafeTimedSerializer(get_settings().secret_key, salt="briefato-csrf").loads(
            form_token, max_age=get_settings().session_ttl_hours * 3600
        )
        return True
    except BadSignature:
        return False


# --------------------------------------------------------------------------- field encryption


def _fernet() -> Fernet:
    settings = get_settings()
    key = settings.field_key
    if not key:
        if settings.is_prod:
            raise RuntimeError("BRIEFATO_FIELD_KEY is required in production")
        # dev/test only: deterministic key derived from the app secret
        digest = hashlib.sha256(f"dev-field-key:{settings.secret_key}".encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_field(plain: str | None) -> str | None:
    if plain is None:
        return None
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_field(token: str | None) -> str:
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


# --------------------------------------------------------------------------- sessions


def login_user(db: Session, user: User, request: Request | None = None) -> str:
    raw, token_hash = new_session_token()
    settings = get_settings()
    db.add(
        AuthSession(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=utcnow() + timedelta(hours=settings.session_ttl_hours),
            ip=(request.client.host if request and request.client else ""),
            user_agent=(request.headers.get("user-agent", "")[:255] if request else ""),
        )
    )
    user.last_login_at = utcnow()
    db.commit()
    audit(db, event="auth.login", user_id=user.id, request=request)
    return raw


def logout_user(db: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    row = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(raw_token)))
    if row and row.revoked_at is None:
        row.revoked_at = utcnow()
        db.commit()


def current_user(request: Request, db: Session) -> User | None:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    row = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(raw)))
    if row is None or row.revoked_at is not None or row.expires_at < utcnow():
        return None
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        return None
    return user


def require_user(request: Request, db: Session) -> User:
    user = current_user(request, db)
    if user is None:
        raise NotAuthenticated
    return user


# --------------------------------------------------------------------------- audit


def audit(
    db: Session,
    *,
    event: str,
    user_id: str | None = None,
    target_type: str = "",
    target_id: str = "",
    request: Request | None = None,
    **meta,
) -> AuditEvent:
    row = AuditEvent(
        id=new_id(),
        user_id=user_id,
        event=event,
        target_type=target_type,
        target_id=target_id,
        ip=(request.client.host if request and request.client else ""),
        user_agent=(request.headers.get("user-agent", "")[:255] if request else ""),
        meta_json=meta or {},
    )
    db.add(row)
    db.commit()
    return row

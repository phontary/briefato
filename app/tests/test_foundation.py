"""Foundation smoke tests — DB, field encryption, password hashing, session lifecycle.

Owner: SYSADMIN (frozen foundation). Run with:
    /workspace/briefato/.venv/bin/python -m pytest app/tests/test_foundation.py -q
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

TMP = tempfile.mkdtemp(prefix="briefato-test-")
os.environ.setdefault("BRIEFATO_DATA_DIR", TMP)
os.environ.setdefault("BRIEFATO_DB_URL", f"sqlite:///{Path(TMP) / 'test.db'}")
os.environ.setdefault("BRIEFATO_LLM_MOCK", "true")
os.environ.setdefault("BRIEFATO_SECRET_KEY", "test-secret")

import pytest  # noqa: E402

from briefato import security  # noqa: E402
from briefato.db import SessionLocal, init_db  # noqa: E402
from briefato.models import Generation, Letter, Patient, Subscription, User, utcnow  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _db():
    init_db()
    yield


def test_schema_creates_all_tables():
    from briefato.db import engine

    from sqlalchemy import inspect

    tables = set(inspect(engine).get_table_names())
    assert {
        "users",
        "auth_sessions",
        "patients",
        "letters",
        "generations",
        "subscriptions",
        "audit_events",
    } <= tables


def test_password_hash_roundtrip():
    h = security.hash_password("Korrekt-Pferd-Batterie-7")
    assert h.startswith("$argon2")
    assert security.verify_password("Korrekt-Pferd-Batterie-7", h)
    assert not security.verify_password("wrong", h)


def test_field_encryption_roundtrip():
    secret = "Patient: Müller, geb. 1974-03-02, Versicherungsnr. A123456789"
    token = security.encrypt_field(secret)
    assert token and token != secret
    assert security.decrypt_field(token) == secret
    assert security.decrypt_field(None) == ""
    assert security.decrypt_field("not-a-token") == ""


def test_session_lifecycle_and_audit():
    db = SessionLocal()
    try:
        user = User(email="arzt@praxis-test.de", password_hash=security.hash_password("geheim-1234"))
        db.add(user)
        db.commit()

        raw = security.login_user(db, user)
        assert raw

        from briefato.models import AuthSession

        row = db.query(AuthSession).filter_by(token_hash=security.hash_token(raw)).one()
        assert row.expires_at > utcnow()

        security.logout_user(db, raw)
        db.refresh(row)
        assert row.revoked_at is not None

        events = {e.event for e in db.query(security.AuditEvent).all()}
        assert "auth.login" in events
    finally:
        db.close()


def test_tenant_columns_present():
    db = SessionLocal()
    try:
        owner = User(email="owner@praxis-test.de", password_hash="x")
        other = User(email="other@praxis-test.de", password_hash="x")
        db.add_all([owner, other])
        db.commit()

        p1 = Patient(user_id=owner.id, last_name="Müller", first_name="Anna")
        p2 = Patient(user_id=other.id, last_name="Schmidt", first_name="Ben")
        db.add_all([p1, p2])
        db.commit()

        db.add(
            Letter(
                user_id=owner.id,
                patient_id=p1.id,
                kind="arztbrief",
                title="Arztbrief Müller",
                dictation_enc=security.encrypt_field("Befund: ..."),
                content_enc=security.encrypt_field("Sehr geehrte ..."),
            )
        )
        db.add(Generation(user_id=owner.id, model="mock", tokens_in=10, tokens_out=20))
        db.add(Subscription(user_id=owner.id, plan_code="starter", letters_quota=40))
        db.commit()

        # tenant scoping is a query-level contract
        assert db.query(Patient).filter_by(user_id=owner.id).count() == 1
        assert db.query(Patient).filter_by(user_id=other.id).count() == 1
        assert db.query(Letter).filter_by(user_id=other.id).count() == 0
    finally:
        db.close()

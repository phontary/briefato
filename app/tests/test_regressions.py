"""Regression tests for two defects found during parent review of the parallel build (2026-10-02).

1. Portal fold-back deleted letters by time window → a letter the member created in a second tab
   while the model was running could be merged and deleted. Fixed by id-difference.
2. Pipeline pseudonymisation leak assertion false-positived when a patient value (e.g. first name)
   also appears in the practice's own letterhead, aborting generation in dev/staging.

Owner: SYSADMIN (release gate).
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

TMP = tempfile.mkdtemp(prefix="briefato-regress-")
os.environ.setdefault("BRIEFATO_DATA_DIR", TMP)
os.environ.setdefault("BRIEFATO_DB_URL", f"sqlite:///{Path(TMP) / 'regress.db'}")
os.environ.setdefault("BRIEFATO_LLM_MOCK", "true")
os.environ.setdefault("BRIEFATO_SECRET_KEY", "regress-secret")
os.environ.setdefault("BRIEFATO_ENV", "staging")

import pytest  # noqa: E402

from briefato import security  # noqa: E402
from briefato.db import SessionLocal, init_db  # noqa: E402
from briefato.models import Letter, Patient, User  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _db():
    init_db()
    yield


def _user(db, email: str) -> User:
    user = User(email=email, password_hash=security.hash_password("x"))
    db.add(user)
    db.commit()
    return user


def test_concurrent_letter_survives_fold_back():
    from briefato.routes.letters import _fold_pipeline_letters, _letter_ids

    db = SessionLocal()
    try:
        user = _user(db, "fold@briefato.test")
        draft = Letter(user_id=user.id, kind="arztbrief", title="Entwurf", status="draft")
        db.add(draft)
        db.commit()

        # ids that existed before the model call
        before_ids = _letter_ids(db, user)

        # during the call: the pipeline creates its row AND the member opens a second tab
        pipeline_row = Letter(user_id=user.id, kind="arztbrief", title="Arztbrief Müller", status="done",
                              content_enc=security.encrypt_field("Sehr geehrte Damen und Herren,"))
        concurrent = Letter(user_id=user.id, kind="attest", title="Attest Schmidt", status="draft")
        db.add_all([pipeline_row, concurrent])
        db.commit()

        _fold_pipeline_letters(db, user, draft, before_ids, pipeline_row)
        db.commit()

        db.refresh(draft)
        assert draft.status == "done"
        # the member's own draft title stays authoritative; only the generated payload is merged
        assert draft.title == "Entwurf"
        assert security.decrypt_field(draft.content_enc).startswith("Sehr geehrte")

        assert db.get(Letter, pipeline_row.id) is None, "pipeline duplicate must be removed"
        assert db.get(Letter, concurrent.id) is not None, "concurrent member letter must survive"
    finally:
        db.close()


def test_no_fold_when_pipeline_creates_nothing():
    from briefato.routes.letters import _fold_pipeline_letters, _letter_ids

    db = SessionLocal()
    try:
        user = _user(db, "nofold@briefato.test")
        draft = Letter(user_id=user.id, kind="arztbrief", title="Entwurf", status="draft")
        db.add(draft)
        db.commit()
        before_ids = _letter_ids(db, user)

        other = Letter(user_id=user.id, kind="befund", title="Befund", status="draft")
        db.add(other)
        db.commit()

        # two new rows exist → ambiguous, the fold must do nothing rather than guess
        class Echo:
            id = "does-not-exist"

        _fold_pipeline_letters(db, user, draft, before_ids, Echo())
        db.commit()
        assert db.get(Letter, draft.id) is not None
        assert db.get(Letter, other.id) is not None
    finally:
        db.close()


def test_letterhead_name_does_not_break_generation():
    """Patient first name identical to a word in the practice letterhead must still generate."""
    from briefato.pipeline.generate import generate_letter

    db = SessionLocal()
    try:
        user = _user(db, "dr.anna@briefato.test")
        user.full_name = "Dr. Anna Beispiel"
        user.letterhead_json = {
            "practice_name": "Praxis Dr. Anna Beispiel",
            "full_name": "Dr. Anna Beispiel",
            "street": "Hauptstraße 1",
            "zip": "10115",
            "city": "Berlin",
        }
        patient = Patient(user_id=user.id, first_name="Anna", last_name="Müller",
                          birth_date=date(1974, 3, 2), insurance_number="A123456789")
        db.add(patient)
        db.commit()

        letter = generate_letter(
            db,
            user=user,
            patient=patient,
            kind="arztbrief",
            dictation="Patientin klagt über Husten seit zwei Wochen, kein Fieber.",
            letterhead=user.letterhead_json,
        )
        assert letter.status == "done"
        text = security.decrypt_field(letter.content_enc)
        assert "Husten" in text
    finally:
        db.close()

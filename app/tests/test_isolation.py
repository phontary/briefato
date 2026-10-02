"""Adversarial tenant-isolation suite: user B must never reach user A's data.

Every route is exercised with A's object ids while authenticated as B. Missing objects
are 404 (never 403, never a silent success). Run:
    cd /workspace/briefato && BRIEFATO_LLM_MOCK=true .venv/bin/python -m pytest app/tests/test_isolation.py -q
"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

TMP = tempfile.mkdtemp(prefix="briefato-isolation-test-")
os.environ["BRIEFATO_DATA_DIR"] = TMP
os.environ["BRIEFATO_DB_URL"] = f"sqlite:///{Path(TMP) / 'isolation.db'}"
os.environ["BRIEFATO_LLM_MOCK"] = "true"
os.environ["BRIEFATO_SECRET_KEY"] = "test-secret-isolation"
os.environ.setdefault("BRIEFATO_ENV", "dev")

import pytest  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from briefato.db import Base, engine, SessionLocal  # noqa: E402
from briefato.main import app  # noqa: E402
from briefato.models import Letter, Patient  # noqa: E402
from briefato.security import encrypt_field  # noqa: E402

PASSWORD = "geheim-1234"


@pytest.fixture(autouse=True)
def _fresh_db():
    from briefato import models  # noqa: F401

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


def new_client(email: str, name: str) -> TestClient:
    client = TestClient(app, follow_redirects=False)
    client.get("/anmelden")
    token = client.cookies.get("briefato_csrf")
    response = client.post(
        "/registrieren",
        data={"csrf_token": token, "email": email, "password": PASSWORD, "full_name": name},
    )
    assert response.status_code == 303, response.text
    return client


def csrf(client: TestClient) -> str:
    token = client.cookies.get("briefato_csrf")
    if not token:
        client.get("/anmelden")
        token = client.cookies.get("briefato_csrf")
    return token


def seed_owner(client: TestClient) -> tuple[str, str]:
    """Create a patient and a generated letter owned by ``client`` (user A)."""
    response = client.post(
        "/app/patienten/neu",
        data={"csrf_token": csrf(client), "last_name": "Geheim", "first_name": "Greta", "insurance_number": "A99999"},
    )
    patient_id = response.headers["location"].split("/")[3].split("?")[0]
    response = client.post(
        "/app/briefe/neu",
        data={
            "csrf_token": csrf(client),
            "patient_id": patient_id,
            "kind": "arztbrief",
            "title": "Vertraulicher Arztbrief",
            "dictation": "Vertrauliches Diktat von Patientin Geheim.",
        },
    )
    letter_id = response.headers["location"].split("/")[3].split("?")[0]
    # store generated content directly (ownership, not generation, is under test)
    db = SessionLocal()
    try:
        letter = db.get(Letter, letter_id)
        letter.content_enc = encrypt_field("Vertraulicher Inhalt nur für A.")
        letter.status = "done"
        db.commit()
    finally:
        db.close()
    return patient_id, letter_id


def assert_owner_untouched(patient_id: str, letter_id: str) -> None:
    db = SessionLocal()
    try:
        patient = db.get(Patient, patient_id)
        letter = db.get(Letter, letter_id)
        assert patient is not None and patient.last_name == "Geheim"
        assert letter is not None
        assert letter.status == "done"
        assert letter.patient_id == patient_id
        assert letter.title == "Vertraulicher Arztbrief"
    finally:
        db.close()


# --------------------------------------------------------------------------- patients


def test_foreign_patient_detail_is_404():
    a = new_client("a@example.de", "Praxis A")
    b = new_client("b@example.de", "Praxis B")
    patient_id, _ = seed_owner(a)

    assert b.get(f"/app/patienten/{patient_id}").status_code == 404
    assert "Geheim" not in b.get(f"/app/patienten/{patient_id}").text


def test_foreign_patient_edit_form_is_404():
    a = new_client("a@example.de", "Praxis A")
    b = new_client("b@example.de", "Praxis B")
    patient_id, _ = seed_owner(a)
    assert b.get(f"/app/patienten/{patient_id}/bearbeiten").status_code == 404


def test_foreign_patient_edit_post_is_404_and_unchanged():
    a = new_client("a@example.de", "Praxis A")
    b = new_client("b@example.de", "Praxis B")
    patient_id, letter_id = seed_owner(a)

    response = b.post(
        f"/app/patienten/{patient_id}/bearbeiten",
        data={"csrf_token": csrf(b), "last_name": "Gekapert", "first_name": "X"},
    )
    assert response.status_code == 404
    db = SessionLocal()
    try:
        assert db.get(Patient, patient_id).last_name == "Geheim"
    finally:
        db.close()
    assert_owner_untouched(patient_id, letter_id)


def test_foreign_patient_archive_is_404_and_unchanged():
    a = new_client("a@example.de", "Praxis A")
    b = new_client("b@example.de", "Praxis B")
    patient_id, letter_id = seed_owner(a)

    response = b.post(f"/app/patienten/{patient_id}/archivieren", data={"csrf_token": csrf(b)})
    assert response.status_code == 404
    db = SessionLocal()
    try:
        assert db.get(Patient, patient_id).archived_at is None
    finally:
        db.close()
    assert_owner_untouched(patient_id, letter_id)


def test_patient_list_never_contains_other_tenant():
    a = new_client("a@example.de", "Praxis A")
    b = new_client("b@example.de", "Praxis B")
    seed_owner(a)

    listing = b.get("/app/patienten")
    assert listing.status_code == 200
    assert "Geheim" not in listing.text
    assert "A99999" not in listing.text


# --------------------------------------------------------------------------- letters


def test_foreign_letter_detail_is_404():
    a = new_client("a@example.de", "Praxis A")
    b = new_client("b@example.de", "Praxis B")
    _, letter_id = seed_owner(a)

    response = b.get(f"/app/briefe/{letter_id}")
    assert response.status_code == 404
    assert "Vertraulicher Inhalt nur für A." not in response.text


def test_foreign_letter_generate_is_404():
    a = new_client("a@example.de", "Praxis A")
    b = new_client("b@example.de", "Praxis B")
    _, letter_id = seed_owner(a)

    response = b.post(
        f"/app/briefe/{letter_id}/erzeugen",
        data={"csrf_token": csrf(b), "dictation": "Fremdes Diktat"},
    )
    assert response.status_code == 404


def test_foreign_letter_save_is_404_and_unchanged():
    a = new_client("a@example.de", "Praxis A")
    b = new_client("b@example.de", "Praxis B")
    patient_id, letter_id = seed_owner(a)

    response = b.post(
        f"/app/briefe/{letter_id}/speichern",
        data={"csrf_token": csrf(b), "content": "Gekapert"},
    )
    assert response.status_code == 404
    assert_owner_untouched(patient_id, letter_id)


def test_foreign_letter_approve_is_404_and_unchanged():
    a = new_client("a@example.de", "Praxis A")
    b = new_client("b@example.de", "Praxis B")
    patient_id, letter_id = seed_owner(a)

    response = b.post(f"/app/briefe/{letter_id}/freigeben", data={"csrf_token": csrf(b)})
    assert response.status_code == 404
    db = SessionLocal()
    try:
        assert db.get(Letter, letter_id).status == "done"
    finally:
        db.close()
    assert_owner_untouched(patient_id, letter_id)


def test_foreign_letter_delete_is_404_and_survives():
    a = new_client("a@example.de", "Praxis A")
    b = new_client("b@example.de", "Praxis B")
    patient_id, letter_id = seed_owner(a)

    response = b.post(f"/app/briefe/{letter_id}/loeschen", data={"csrf_token": csrf(b)})
    assert response.status_code == 404
    assert_owner_untouched(patient_id, letter_id)


def test_foreign_letter_export_is_404():
    a = new_client("a@example.de", "Praxis A")
    b = new_client("b@example.de", "Praxis B")
    _, letter_id = seed_owner(a)

    response = b.get(f"/app/briefe/{letter_id}/export.docx")
    assert response.status_code == 404


def test_create_letter_for_foreign_patient_is_404():
    a = new_client("a@example.de", "Praxis A")
    b = new_client("b@example.de", "Praxis B")
    patient_id, _ = seed_owner(a)

    response = b.post(
        "/app/briefe/neu",
        data={
            "csrf_token": csrf(b),
            "patient_id": patient_id,
            "kind": "arztbrief",
            "title": "Gekaperter Brief",
            "dictation": "Fremd",
        },
    )
    assert response.status_code == 404
    db = SessionLocal()
    try:
        assert db.query(Letter).filter_by(patient_id=patient_id).count() == 1  # only A's own letter
        assert db.query(Letter).filter_by(title="Gekaperter Brief").count() == 0
    finally:
        db.close()


def test_letter_list_never_contains_other_tenant():
    a = new_client("a@example.de", "Praxis A")
    b = new_client("b@example.de", "Praxis B")
    _, letter_id = seed_owner(a)

    listing = b.get("/app/briefe")
    assert listing.status_code == 200
    assert "Vertraulicher Arztbrief" not in listing.text
    assert letter_id not in listing.text


# --------------------------------------------------------------------------- guessing ids & search


def test_guessed_ids_are_404():
    b = new_client("b@example.de", "Praxis B")
    for _ in range(5):
        guess = uuid.uuid4().hex
        assert b.get(f"/app/patienten/{guess}").status_code == 404
        assert b.get(f"/app/briefe/{guess}").status_code == 404
        assert b.get(f"/app/briefe/{guess}/export.docx").status_code == 404


def test_search_is_tenant_scoped():
    a = new_client("a@example.de", "Praxis A")
    b = new_client("b@example.de", "Praxis B")
    seed_owner(a)
    b.post(
        "/app/patienten/neu",
        data={"csrf_token": csrf(b), "last_name": "Eigen", "first_name": "Emil"},
    )

    # B searches for A's data by name and by letter text
    by_name = b.get("/app/suche", params={"q": "Geheim"})
    assert "Greta" not in by_name.text
    assert "0 Treffer" in by_name.text

    by_text = b.get("/app/suche", params={"q": "Vertraulicher Inhalt"})
    assert "Vertraulicher Arztbrief" not in by_text.text
    assert "0 Treffer" in by_text.text

    # B's own data is still findable
    own = b.get("/app/suche", params={"q": "Eigen"})
    assert "Emil" in own.text


def test_dashboard_and_account_export_exclude_other_tenant():
    a = new_client("a@example.de", "Praxis A")
    b = new_client("b@example.de", "Praxis B")
    seed_owner(a)

    dashboard = b.get("/app")
    assert "Vertraulicher Arztbrief" not in dashboard.text

    exported = b.get("/app/konto/export").json()
    assert exported["patients"] == []
    assert exported["letters"] == []

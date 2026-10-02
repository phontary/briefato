"""Portal end-to-end tests (FastAPI TestClient, mock LLM, no network).

Run:
    cd /workspace/briefato && BRIEFATO_LLM_MOCK=true .venv/bin/python -m pytest app/tests/test_portal.py -q
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

TMP = tempfile.mkdtemp(prefix="briefato-portal-test-")
os.environ["BRIEFATO_DATA_DIR"] = TMP
os.environ["BRIEFATO_DB_URL"] = f"sqlite:///{Path(TMP) / 'portal.db'}"
os.environ["BRIEFATO_LLM_MOCK"] = "true"
os.environ["BRIEFATO_SECRET_KEY"] = "test-secret-portal"
os.environ.setdefault("BRIEFATO_ENV", "dev")

import pytest  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from briefato import billing  # noqa: E402
from briefato.config import get_settings  # noqa: E402
from briefato.db import Base, engine  # noqa: E402
from briefato.main import app  # noqa: E402
from briefato.models import AuditEvent, Letter, Patient, Subscription, User  # noqa: E402
from briefato.pipeline import generate as pipeline_generate  # noqa: E402
from briefato.security import decrypt_field, encrypt_field  # noqa: E402

PASSWORD = "geheim-1234"


@pytest.fixture(autouse=True)
def _fresh_db():
    from briefato import models  # noqa: F401

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    get_settings().ensure_dirs()
    yield


@pytest.fixture
def client():
    with TestClient(app, follow_redirects=False) as test_client:
        yield test_client


def csrf(client: TestClient) -> str:
    if not client.cookies.get("briefato_csrf"):
        client.get("/anmelden")
    return client.cookies.get("briefato_csrf")


def register(client: TestClient, email: str = "arzt@example.de", full_name: str = "Dr. Anna Beispiel"):
    return client.post(
        "/registrieren",
        data={
            "csrf_token": csrf(client),
            "email": email,
            "password": PASSWORD,
            "full_name": full_name,
            "practice_name": "Praxis Beispiel",
        },
    )


def login(client: TestClient, email: str = "arzt@example.de", password: str = PASSWORD):
    return client.post(
        "/anmelden",
        data={"csrf_token": csrf(client), "email": email, "password": password},
    )


def create_patient(client: TestClient, last_name: str = "Müller", first_name: str = "Anna") -> str:
    response = client.post(
        "/app/patienten/neu",
        data={
            "csrf_token": csrf(client),
            "last_name": last_name,
            "first_name": first_name,
            "city": "Musterstadt",
            "insurance": "TK",
        },
    )
    assert response.status_code == 303, response.text
    return response.headers["location"].split("/")[3].split("?")[0]


def create_letter(client: TestClient, patient_id: str, dictation: str = "Rückenschmerzen seit drei Wochen.") -> str:
    response = client.post(
        "/app/briefe/neu",
        data={
            "csrf_token": csrf(client),
            "patient_id": patient_id,
            "kind": "arztbrief",
            "title": "Arztbrief Müller",
            "dictation": dictation,
        },
    )
    assert response.status_code == 303, response.text
    return response.headers["location"].split("/")[3].split("?")[0]


def fake_generate(db, *, user, patient, kind, dictation, letterhead, extra=""):
    """Simulates WORKSTREAM-PIPELINE's generate_letter without network access."""
    return SimpleNamespace(
        id="generated-not-persisted",
        user_id=user.id,
        kind=kind,
        status="done",
        content_enc=encrypt_field(f"Sehr geehrte Damen und Herren,\n\n{dictation}\n\nMit freundlichen Grüßen"),
        model="mock-model",
        tokens_in=42,
        tokens_out=128,
        cost_usd=0.0,
    )


# --------------------------------------------------------------------------- public


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_landing_and_legal_pages(client):
    for path in ("/", "/preise", "/impressum", "/datenschutz", "/agb"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert "text/html" in response.headers["content-type"]
        assert "Briefato" in response.text


def test_assets_served(client):
    response = client.get("/assets/css/app.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
    assert response.text.strip()


def test_asset_path_traversal_blocked(client):
    for path in ("/assets/../briefato/config.py", "/assets/..%2F..%2Fconfig.py", "/assets/%2e%2e/config.py"):
        response = client.get(path)
        assert response.status_code in (400, 404), path


def test_unknown_path_returns_custom_404(client):
    response = client.get("/gibt-es-nicht")
    assert response.status_code == 404
    assert "Seite nicht gefunden" in response.text


def test_security_headers_present(client):
    response = client.get("/anmelden")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


# --------------------------------------------------------------------------- auth


def test_unauthenticated_app_redirects_to_login(client):
    response = client.get("/app")
    assert response.status_code == 303
    assert response.headers["location"].startswith("/anmelden?next=")


def test_register_login_logout_flow(client):
    response = register(client)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/app")
    assert client.cookies.get("briefato_session")

    # dashboard reachable while logged in
    assert client.get("/app").status_code == 200

    # logout invalidates the session
    response = client.post("/abmelden", data={"csrf_token": csrf(client)})
    assert response.status_code == 303
    assert response.headers["location"].startswith("/")
    assert client.get("/app").status_code == 303

    # can log back in
    assert login(client).status_code == 303
    assert client.get("/app").status_code == 200


def test_register_validation_errors(client):
    response = client.post(
        "/registrieren",
        data={"csrf_token": csrf(client), "email": "keine-mail", "password": "kurz", "full_name": "A"},
    )
    assert response.status_code == 400
    assert "gültige E-Mail-Adresse" in response.text
    assert "mindestens 8 Zeichen" in response.text
    assert response.text.count('aria-invalid="true"') >= 2


def test_register_duplicate_email(client):
    assert register(client).status_code == 303
    client.post("/abmelden", data={"csrf_token": csrf(client)})
    response = register(client)
    assert response.status_code == 400
    assert "bereits registriert" in response.text


def test_login_wrong_password_is_generic(client):
    register(client)
    client.post("/abmelden", data={"csrf_token": csrf(client)})
    response = login(client, password="falsch-falsch")
    assert response.status_code == 401
    assert "E-Mail-Adresse oder Passwort ist nicht korrekt." in response.text
    # no user enumeration: an unknown address yields the same message
    response = login(client, email="unbekannt@example.de", password="falsch-falsch")
    assert response.status_code == 401
    assert "E-Mail-Adresse oder Passwort ist nicht korrekt." in response.text


def test_login_throttling(client):
    settings = get_settings()
    original = settings.login_max_attempts
    settings.login_max_attempts = 3
    try:
        register(client)
        client.post("/abmelden", data={"csrf_token": csrf(client)})
        for _ in range(3):
            assert login(client, password="falsch-falsch").status_code == 401
        response = login(client, password="falsch-falsch")
        assert response.status_code == 429
        assert "Zu viele Fehlversuche" in response.text
    finally:
        settings.login_max_attempts = original


def test_csrf_token_required(client):
    # no token at all
    response = client.post("/registrieren", data={"email": "x@example.de", "password": "geheim-1234"})
    assert response.status_code == 403
    # token that does not match the cookie
    response = client.post(
        "/registrieren",
        data={"csrf_token": "manipuliert", "email": "x@example.de", "password": "geheim-1234"},
    )
    assert response.status_code == 403


def test_password_forgot_is_neutral_and_audits(client):
    register(client)
    client.post("/abmelden", data={"csrf_token": csrf(client)})
    response = client.post("/passwort-vergessen", data={"csrf_token": csrf(client), "email": "arzt@example.de"})
    assert response.status_code == 200
    assert "E-Mail-Versand ist in dieser Version noch nicht aktiviert" in response.text

    from briefato.db import SessionLocal

    db = SessionLocal()
    try:
        events = {e.event for e in db.query(AuditEvent).all()}
    finally:
        db.close()
    assert "auth.password_reset_requested" in events


def test_password_reset_rejects_invalid_token(client):
    register(client)
    client.post("/abmelden", data={"csrf_token": csrf(client)})
    response = client.post(
        "/passwort-zuruecksetzen",
        data={"csrf_token": csrf(client), "token": "ungueltig", "email": "arzt@example.de", "password": "neues-passwort"},
    )
    assert response.status_code == 400
    assert "ungültig oder abgelaufen" in response.text


# --------------------------------------------------------------------------- dashboard & patients


def test_dashboard_counts(client):
    register(client)
    patient_id = create_patient(client)
    create_letter(client, patient_id)
    response = client.get("/app")
    assert response.status_code == 200
    assert "Übersicht" in response.text
    assert "Patienten" in response.text
    assert "Kontingent übrig" in response.text


def test_patient_crud_and_archive(client):
    register(client)
    patient_id = create_patient(client, last_name="Schmidt", first_name="Ben")

    detail = client.get(f"/app/patienten/{patient_id}")
    assert detail.status_code == 200
    assert "Schmidt" in detail.text

    listing = client.get("/app/patienten")
    assert "Schmidt" in listing.text

    edit_form = client.get(f"/app/patienten/{patient_id}/bearbeiten")
    assert edit_form.status_code == 200
    assert "Schmidt" in edit_form.text

    updated = client.post(
        f"/app/patienten/{patient_id}/bearbeiten",
        data={
            "csrf_token": csrf(client),
            "last_name": "Schmidt",
            "first_name": "Benjamin",
            "city": "Beispielstadt",
            "notes": "Interne Notiz",
        },
    )
    assert updated.status_code == 303

    from briefato.db import SessionLocal

    db = SessionLocal()
    try:
        patient = db.get(Patient, patient_id)
        assert patient.first_name == "Benjamin"
        assert decrypt_field(patient.notes_enc) == "Interne Notiz"
    finally:
        db.close()

    archived = client.post(f"/app/patienten/{patient_id}/archivieren", data={"csrf_token": csrf(client)})
    assert archived.status_code == 303
    assert "Schmidt" not in client.get("/app/patienten").text
    assert "Schmidt" in client.get("/app/patienten?archiviert=1").text


def test_patient_create_requires_names(client):
    register(client)
    response = client.post(
        "/app/patienten/neu",
        data={"csrf_token": csrf(client), "last_name": "", "first_name": ""},
    )
    assert response.status_code == 400
    assert "Nachnamen" in response.text
    assert "Vornamen" in response.text


# --------------------------------------------------------------------------- letters


def test_letter_create_generate_approve_flow(client, monkeypatch):
    register(client)
    patient_id = create_patient(client)
    letter_id = create_letter(client, patient_id, dictation="Akute Lumbalgie ohne Ausstrahlung.")

    monkeypatch.setattr(pipeline_generate, "generate_letter", fake_generate)

    # generate (non-HTMX: redirect back to the detail page)
    generated = client.post(
        f"/app/briefe/{letter_id}/erzeugen",
        data={"csrf_token": csrf(client), "dictation": "Akute Lumbalgie ohne Ausstrahlung."},
    )
    assert generated.status_code == 303

    detail = client.get(f"/app/briefe/{letter_id}")
    assert "Sehr geehrte Damen und Herren" in detail.text
    assert "Freigeben" in detail.text

    approved = client.post(f"/app/briefe/{letter_id}/freigeben", data={"csrf_token": csrf(client)})
    assert approved.status_code == 303

    detail = client.get(f"/app/briefe/{letter_id}")
    assert "Freigegeben" in detail.text
    assert 'id="content"' not in detail.text  # locked: no editable textarea

    # generating an approved letter is refused
    blocked = client.post(
        f"/app/briefe/{letter_id}/erzeugen",
        data={"csrf_token": csrf(client), "dictation": "Neu"},
    )
    assert "gesperrt" in blocked.text


def test_letter_generate_htmx_returns_partial(client, monkeypatch):
    register(client)
    patient_id = create_patient(client)
    letter_id = create_letter(client, patient_id)
    monkeypatch.setattr(pipeline_generate, "generate_letter", fake_generate)

    response = client.post(
        f"/app/briefe/{letter_id}/erzeugen",
        data={"csrf_token": csrf(client), "dictation": "Kontrolle in zwei Wochen."},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert "Sehr geehrte Damen und Herren" in response.text
    assert "<html" not in response.text
    assert 'id="brief-editor"' in response.text


def test_letter_save_edits_content(client, monkeypatch):
    register(client)
    patient_id = create_patient(client)
    letter_id = create_letter(client, patient_id)
    monkeypatch.setattr(pipeline_generate, "generate_letter", fake_generate)
    client.post(f"/app/briefe/{letter_id}/erzeugen", data={"csrf_token": csrf(client), "dictation": "Text"})

    saved = client.post(
        f"/app/briefe/{letter_id}/speichern",
        data={"csrf_token": csrf(client), "content": "Überarbeiteter Brieftext."},
    )
    assert saved.status_code == 303
    assert "Überarbeiteter Brieftext." in client.get(f"/app/briefe/{letter_id}").text


def test_letter_export_docx(client, monkeypatch):
    register(client)
    patient_id = create_patient(client, last_name="Müller")
    letter_id = create_letter(client, patient_id)
    monkeypatch.setattr(pipeline_generate, "generate_letter", fake_generate)
    client.post(f"/app/briefe/{letter_id}/erzeugen", data={"csrf_token": csrf(client), "dictation": "Text"})

    captured = {}

    def fake_render_docx(letter_text, letterhead, patient_ctx, out_path, kind):
        captured["letterhead"] = letterhead
        captured["patient_ctx"] = patient_ctx
        Path(out_path).write_bytes(b"PK\x03\x04briefato-docx")
        return Path(out_path)

    monkeypatch.setattr(pipeline_generate, "render_docx", fake_render_docx)

    response = client.get(f"/app/briefe/{letter_id}/export.docx")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert ".docx" in response.headers["content-disposition"]
    assert response.content.startswith(b"PK")
    assert captured["patient_ctx"]["last_name"] == "Müller"


def test_letter_delete(client):
    register(client)
    patient_id = create_patient(client)
    letter_id = create_letter(client, patient_id)
    response = client.post(f"/app/briefe/{letter_id}/loeschen", data={"csrf_token": csrf(client)})
    assert response.status_code == 303

    from briefato.db import SessionLocal

    db = SessionLocal()
    try:
        assert db.get(Letter, letter_id) is None
    finally:
        db.close()
    assert client.get(f"/app/briefe/{letter_id}").status_code == 404


def test_quota_exhausted_shows_german_error(client, monkeypatch):
    register(client)
    patient_id = create_patient(client)
    letter_id = create_letter(client, patient_id)
    monkeypatch.setattr(
        billing,
        "quota_state",
        lambda db, user: {"plan": "free", "quota": 10, "used": 10, "remaining": 0, "period_end": None},
    )
    response = client.post(
        f"/app/briefe/{letter_id}/erzeugen",
        data={"csrf_token": csrf(client), "dictation": "Text"},
    )
    assert response.status_code == 402
    assert "Kontingent ist aufgebraucht" in response.text


def test_generate_failure_shows_german_error(client, monkeypatch):
    """A pipeline failure must surface a plain German message and the HTTP error, never a stack trace."""
    register(client)
    patient_id = create_patient(client)
    letter_id = create_letter(client, patient_id)

    def boom(db, *, user, patient, kind, dictation, letterhead, extra=""):
        raise RuntimeError("provider exploded: secret-ish internal detail")

    monkeypatch.setattr(pipeline_generate, "generate_letter", boom)
    response = client.post(
        f"/app/briefe/{letter_id}/erzeugen",
        data={"csrf_token": csrf(client), "dictation": "Text"},
    )
    assert response.status_code == 502
    assert "konnte nicht erzeugt werden" in response.text
    assert "provider exploded" not in response.text
    assert "Traceback" not in response.text


def test_real_pipeline_generates_letter_offline(client):
    """Integration with the actual (mock-provider) pipeline: exactly one letter, content stored."""
    register(client, full_name="Dr. Beispiel", email="pipeline@example.de")
    patient_id = create_patient(client, last_name="Musterfrau", first_name="Greta")
    letter_id = create_letter(client, patient_id, dictation="Seit drei Wochen Rueckenschmerzen ohne Ausstrahlung.")

    response = client.post(
        f"/app/briefe/{letter_id}/erzeugen",
        data={"csrf_token": csrf(client), "dictation": "Seit drei Wochen Rueckenschmerzen ohne Ausstrahlung."},
    )
    assert response.status_code == 303, response.text
    detail = client.get(f"/app/briefe/{letter_id}")
    assert "Rueckenschmerzen" in detail.text
    assert "Freigeben" in detail.text

    from briefato.db import SessionLocal

    db = SessionLocal()
    try:
        letters = db.query(Letter).all()
        assert len(letters) == 1, "the pipeline's transient letter row must be folded into the draft"
        assert letters[0].content_enc
        subscription = db.query(Subscription).first()
        assert subscription.letters_used == 1
    finally:
        db.close()


def test_search_finds_own_patient_and_letter(client, monkeypatch):
    register(client)
    patient_id = create_patient(client, last_name="Suchname", first_name="Erika")
    letter_id = create_letter(client, patient_id, dictation="Besonderes Suchwort Bergziege")
    monkeypatch.setattr(pipeline_generate, "generate_letter", fake_generate)
    client.post(f"/app/briefe/{letter_id}/erzeugen", data={"csrf_token": csrf(client), "dictation": "Besonderes Suchwort Bergziege"})

    by_name = client.get("/app/suche", params={"q": "Suchname"})
    assert "Erika" in by_name.text

    by_content = client.get("/app/suche", params={"q": "Bergziege"})
    assert "Arztbrief Müller" in by_content.text


# --------------------------------------------------------------------------- account & billing


def test_account_view_and_export(client):
    register(client, email="konto@example.de")
    patient_id = create_patient(client)
    create_letter(client, patient_id)

    page = client.get("/app/konto")
    assert page.status_code == 200
    assert "konto@example.de" in page.text
    assert "Briefkopf" in page.text

    exported = client.get("/app/konto/export")
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("application/json")
    payload = exported.json()
    assert payload["account"]["email"] == "konto@example.de"
    assert len(payload["patients"]) == 1
    assert len(payload["letters"]) == 1
    assert "password_hash" not in str(payload)


def test_account_profile_and_letterhead_update(client):
    register(client)
    response = client.post(
        "/app/konto/profil",
        data={"csrf_token": csrf(client), "full_name": "Dr. Neu", "phone": "0123"},
    )
    assert response.status_code == 303
    response = client.post(
        "/app/konto/briefkopf",
        data={"csrf_token": csrf(client), "lh_name": "Praxis Neu", "lh_subtitle": "Allgemeinmedizin"},
    )
    assert response.status_code == 303

    from briefato.db import SessionLocal

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email="arzt@example.de").one()
        assert user.full_name == "Dr. Neu"
        assert user.letterhead_json["name"] == "Praxis Neu"
    finally:
        db.close()


def test_account_deletion_request(client):
    register(client, email="weg@example.de")
    response = client.post("/app/konto/loeschen", data={"csrf_token": csrf(client), "confirm": "ja"})
    assert response.status_code == 303

    from briefato.db import SessionLocal

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email="weg@example.de").one()
        assert user.is_active is False
    finally:
        db.close()

    assert client.get("/app").status_code == 303
    assert login(client, email="weg@example.de").status_code == 401


def test_billing_unavailable_is_graceful(client):
    register(client)
    response = client.get("/app/abrechnung")
    assert response.status_code == 200
    assert "noch nicht verfügbar" in response.text


def test_billing_checkout_redirect_when_available(client, monkeypatch):
    register(client)
    monkeypatch.setattr(billing, "create_checkout_url", lambda db, user, plan, success_url, cancel_url: "https://checkout.example/session")
    response = client.get("/app/abrechnung", params={"plan": "praxis"})
    assert response.status_code == 303
    assert response.headers["location"] == "https://checkout.example/session"


def test_stripe_webhook_uses_billing_module(client, monkeypatch):
    monkeypatch.setattr(
        billing, "handle_webhook", lambda db, payload, sig: {"handled": True, "event": "checkout.session.completed"}
    )
    response = client.post("/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t=1"})
    assert response.status_code == 200
    assert response.json() == {"handled": True, "event": "checkout.session.completed"}


def test_admin_requires_login(client):
    response = client.get("/admin/", follow_redirects=False)
    assert response.status_code in (302, 303, 307)
    assert "/admin/login" in response.headers.get("location", "")

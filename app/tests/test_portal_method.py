"""Method UI tests: plain-text editor, /app/methode, /app/vorlagen and the proposal flow.

Run:
    cd /workspace/briefato && BRIEFATO_LLM_MOCK=true .venv/bin/python -m pytest app/tests/test_portal_method.py -q
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

TMP = tempfile.mkdtemp(prefix="briefato-method-test-")
os.environ["BRIEFATO_DATA_DIR"] = TMP
os.environ["BRIEFATO_DB_URL"] = f"sqlite:///{Path(TMP) / 'method.db'}"
os.environ["BRIEFATO_LLM_MOCK"] = "true"
os.environ["BRIEFATO_SECRET_KEY"] = "test-secret-method"
os.environ.setdefault("BRIEFATO_ENV", "dev")

import pytest  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from briefato.db import Base, engine, SessionLocal  # noqa: E402
from briefato.main import app  # noqa: E402
from briefato.models import AuditEvent, Letter, User  # noqa: E402
from briefato.pipeline import generate as pipeline_generate  # noqa: E402
from briefato.routes import brain_bridge  # noqa: E402
from briefato.routes.library_models import TemplateProposal  # noqa: E402
from briefato.security import encrypt_field  # noqa: E402

PASSWORD = "geheim-1234"
LOCKED = ("Cholezystolithiasis.md", "Acne-inversa.md", "Struma_nodosa_Hyperthyreose.md")


@pytest.fixture(autouse=True)
def _fresh_db():
    from briefato import models  # noqa: F401
    from briefato.routes import library_models  # noqa: F401

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    with TestClient(app, follow_redirects=False) as test_client:
        yield test_client


def csrf(client: TestClient) -> str:
    if not client.cookies.get("briefato_csrf"):
        client.get("/anmelden")
    return client.cookies.get("briefato_csrf")


def register(client: TestClient, email: str = "arzt@example.de", full_name: str = "Dr. Anna Beispiel") -> None:
    response = client.post(
        "/registrieren",
        data={
            "csrf_token": csrf(client),
            "email": email,
            "password": PASSWORD,
            "full_name": full_name,
            "practice_name": "Praxis Beispiel",
        },
    )
    assert response.status_code == 303, response.text


def make_admin(email: str = "arzt@example.de") -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).one()
        user.is_admin = True
        db.commit()
    finally:
        db.close()


def create_patient(client: TestClient, last_name: str = "Müller", first_name: str = "Anna") -> str:
    response = client.post(
        "/app/patienten/neu",
        data={"csrf_token": csrf(client), "last_name": last_name, "first_name": first_name},
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


def fake_generate(content: str = "Sehr geehrte Damen und Herren,\n\nBefundtext.\n\nMit freundlichen Grüßen"):
    def _generate(db, *, user, patient, kind, dictation, letterhead, extra=""):
        _generate.captured_extra = extra
        _generate.captured_letterhead = letterhead
        return SimpleNamespace(
            id="generated-not-persisted",
            user_id=user.id,
            kind=kind,
            status="done",
            content_enc=encrypt_field(content),
            model="mock-model",
            tokens_in=42,
            tokens_out=128,
            cost_usd=0.0,
        )

    _generate.captured_extra = ""
    _generate.captured_letterhead = {}
    return _generate


# --------------------------------------------------------------------------- /app/methode


def test_methode_page_lists_kern_rules_and_anti_patterns(client):
    register(client)
    response = client.get("/app/methode")
    assert response.status_code == 200
    body = response.text
    assert "Kern" in body
    assert "K1.1" in body                      # a Kern rule id
    assert "Regelwerk" in body and "R1" in body and "R67" in body
    assert "Anti-Patterns" in body and "AP-01" in body
    assert "Meine Regeln" in body
    assert "nicht außer Kraft" in body or "außer Kraft" in body


def test_methode_custom_rules_roundtrip_and_prompt_passthrough(client, monkeypatch):
    register(client)
    saved = client.post(
        "/app/methode/regeln",
        data={"csrf_token": csrf(client), "custom_rules": "Verwende immer „Pat.“ statt „Patient/in“."},
    )
    assert saved.status_code == 303

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email="arzt@example.de").one()
        assert user.letterhead_json.get("custom_rules") == "Verwende immer „Pat.“ statt „Patient/in“."
    finally:
        db.close()

    page = client.get("/app/methode")
    assert "Verwende immer" in page.text

    # The member rules live on the letterhead payload the portal forwards to the pipeline,
    # which the brain's prompt assembly consumes as ``custom_rules`` (after the Kern).
    generate = fake_generate()
    monkeypatch.setattr(pipeline_generate, "generate_letter", generate)
    patient_id = create_patient(client)
    letter_id = create_letter(client, patient_id)
    client.post(
        f"/app/briefe/{letter_id}/erzeugen",
        data={"csrf_token": csrf(client), "dictation": "Text", "doc_type": "auto"},
    )
    assert generate.captured_letterhead.get("custom_rules") == "Verwende immer „Pat.“ statt „Patient/in“."


def test_methode_requires_auth_and_csrf(client):
    assert client.get("/app/methode").status_code == 303
    register(client)
    assert client.post("/app/methode/regeln", data={"custom_rules": "x"}).status_code == 403


# --------------------------------------------------------------------------- /app/vorlagen


def test_vorlagen_library_browse_and_search(client):
    register(client)
    response = client.get("/app/vorlagen")
    assert response.status_code == 200
    assert "Vorlage vorschlagen" in response.text
    # The governed templates are visible but locked, never linked for retrieval.
    assert "gesperrt (Prüfung ausstehend)" in response.text

    for name in LOCKED:
        entry = brain_bridge.template_entry(name)
        assert entry is not None, name
        assert name in client.get("/app/vorlagen").text or entry["title"] in client.get("/app/vorlagen").text

    searched = client.get("/app/vorlagen", params={"q": "Atherom"})
    assert searched.status_code == 200
    assert "Atherom" in searched.text


def test_vorlagen_detail_renders_text_and_locked_is_unreachable(client):
    register(client)
    response = client.get("/app/vorlagen/Atherom.md")
    assert response.status_code == 200
    assert "Vorlagentext" in response.text
    assert "Vorlage vorschlagen" in response.text

    for name in LOCKED:
        assert client.get(f"/app/vorlagen/{name}").status_code == 404, name


def test_vorlagen_licence_review_is_marked_internal(client):
    register(client)
    response = client.get("/app/vorlagen/Coxarthrose_Exsikkose_Sturz.md")
    assert response.status_code == 200
    assert "nur intern – Referenz" in response.text


def test_vorlagen_unknown_file_is_404(client):
    register(client)
    assert client.get("/app/vorlagen/Gibt-Es-Nicht.md").status_code == 404


# --------------------------------------------------------------------------- proposals


def test_proposal_create_and_member_view(client):
    register(client)
    response = client.post(
        "/app/vorlagen/vorschlag",
        data={"csrf_token": csrf(client), "diagnosis": "Eigene Diagnose XYZ", "sections": "Klinik, Therapie"},
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/app/vorlagen/vorschlaege")

    listing = client.get("/app/vorlagen/vorschlaege")
    assert listing.status_code == 200
    assert "Eigene Diagnose XYZ" in listing.text
    assert "Offen" in listing.text

    db = SessionLocal()
    try:
        proposal = db.query(TemplateProposal).filter_by(diagnosis="Eigene Diagnose XYZ").one()
        assert proposal.status == "pending"
    finally:
        db.close()


def test_proposal_requires_diagnosis(client):
    register(client)
    response = client.post(
        "/app/vorlagen/vorschlag",
        data={"csrf_token": csrf(client), "diagnosis": "   ", "sections": "Klinik"},
    )
    assert response.status_code == 303
    assert "vorschlag_ungueltig" in response.headers["location"]

    db = SessionLocal()
    try:
        assert db.query(TemplateProposal).count() == 0
    finally:
        db.close()


def test_proposals_are_tenant_scoped(client):
    register(client, email="a@example.de", full_name="Praxis A")
    client.post(
        "/app/vorlagen/vorschlag",
        data={"csrf_token": csrf(client), "diagnosis": "Vorschlag von A", "sections": "Klinik"},
    )

    # second member in a separate session
    b = TestClient(app, follow_redirects=False)
    b.get("/anmelden")
    b.post(
        "/registrieren",
        data={"csrf_token": b.cookies.get("briefato_csrf"), "email": "b@example.de",
              "password": PASSWORD, "full_name": "Praxis B"},
    )
    listing = b.get("/app/vorlagen/vorschlaege")
    assert listing.status_code == 200
    assert "Vorschlag von A" not in listing.text

    # B cannot act on A's proposal id via the admin endpoint either (non-admin → 403)
    db = SessionLocal()
    try:
        proposal_id = db.query(TemplateProposal).one().id
    finally:
        db.close()
    assert b.get("/admin/vorlagen-vorschlaege").status_code == 403
    assert b.post(
        f"/admin/vorlagen-vorschlaege/{proposal_id}/genehmigen", data={"csrf_token": csrf(b)}
    ).status_code == 403


# --------------------------------------------------------------------------- admin review


def test_admin_proposals_require_admin_and_login(client):
    # anonymous → redirected to the portal login
    anon = TestClient(app, follow_redirects=False)
    response = anon.get("/admin/vorlagen-vorschlaege")
    assert response.status_code == 303
    assert response.headers["location"].startswith("/anmelden")

    register(client)
    assert client.get("/admin/vorlagen-vorschlaege").status_code == 403


def test_admin_can_approve_proposal_and_it_is_audited(client):
    register(client)
    client.post(
        "/app/vorlagen/vorschlag",
        data={"csrf_token": csrf(client), "diagnosis": "Wird angenommen", "sections": "Klinik"},
    )
    make_admin()

    page = client.get("/admin/vorlagen-vorschlaege")
    assert page.status_code == 200
    assert "Wird angenommen" in page.text
    assert "Annehmen" in page.text

    db = SessionLocal()
    try:
        proposal_id = db.query(TemplateProposal).one().id
    finally:
        db.close()

    response = client.post(
        f"/admin/vorlagen-vorschlaege/{proposal_id}/genehmigen",
        data={"csrf_token": csrf(client), "review_note": "Freigegeben für die Bibliothek."},
    )
    assert response.status_code == 303

    db = SessionLocal()
    try:
        proposal = db.get(TemplateProposal, proposal_id)
        assert proposal.status == "approved"
        assert proposal.reviewed_at is not None
        assert proposal.reviewed_by
        events = {event.event for event in db.query(AuditEvent).all()}
    finally:
        db.close()
    assert "template_proposal.approved" in events


def test_admin_can_reject_proposal(client):
    register(client)
    client.post(
        "/app/vorlagen/vorschlag",
        data={"csrf_token": csrf(client), "diagnosis": "Wird abgelehnt", "sections": ""},
    )
    make_admin()
    db = SessionLocal()
    try:
        proposal_id = db.query(TemplateProposal).one().id
    finally:
        db.close()

    response = client.post(
        f"/admin/vorlagen-vorschlaege/{proposal_id}/ablehnen",
        data={"csrf_token": csrf(client), "review_note": "Doppelt vorhanden."},
    )
    assert response.status_code == 303
    db = SessionLocal()
    try:
        assert db.get(TemplateProposal, proposal_id).status == "rejected"
    finally:
        db.close()


def test_approving_does_not_touch_the_read_only_archive(client):
    """Approval flips the status and audits; the brain archive must stay byte-identical."""
    register(client)
    client.post(
        "/app/vorlagen/vorschlag",
        data={"csrf_token": csrf(client), "diagnosis": "Nur Statusänderung", "sections": "Klinik"},
    )
    make_admin()

    sample = Path("/workspace/schreibdienst/musterbriefe/Atherom.md")
    before = sample.read_bytes() if sample.is_file() else None
    archive_files = sorted(p.name for p in sample.parent.glob("*.md")) if sample.parent.is_dir() else []

    db = SessionLocal()
    try:
        proposal_id = db.query(TemplateProposal).one().id
    finally:
        db.close()
    client.post(
        f"/admin/vorlagen-vorschlaege/{proposal_id}/genehmigen",
        data={"csrf_token": csrf(client), "review_note": ""},
    )

    if before is not None:
        assert sample.read_bytes() == before
        assert sorted(p.name for p in sample.parent.glob("*.md")) == archive_files


# --------------------------------------------------------------------------- letter editor


def test_editor_shows_copy_button_and_rule_check(client, monkeypatch):
    register(client)
    monkeypatch.setattr(
        brain_bridge,
        "check_rules",
        lambda text, doc_type, dictation="": {
            "source": "methode",
            "available": True,
            "clean": False,
            "findings": [{"rule": "R21", "message": "Keine Diagnoseliste am Dokumentende gefunden.", "severity": "hard"}],
            "rules_total": 67,
        },
    )
    monkeypatch.setattr(brain_bridge, "search_templates", lambda text, limit=5: [
        {"file": "Atherom.md", "title": "Atherom (Grützbeutel)", "score": 1.2}
    ])
    monkeypatch.setattr(pipeline_generate, "generate_letter", fake_generate())

    patient_id = create_patient(client)
    letter_id = create_letter(client, patient_id)
    generated = client.post(
        f"/app/briefe/{letter_id}/erzeugen",
        data={"csrf_token": csrf(client), "dictation": "Atherom am Rücken.", "doc_type": "auto"},
    )
    assert generated.status_code == 303

    detail = client.get(f"/app/briefe/{letter_id}")
    assert detail.status_code == 200
    body = detail.text
    # plain-text primary output with a prominent copy button
    assert "Text kopieren" in body
    assert 'data-copy-target="#text-result"' in body
    assert 'id="text-result"' in body
    # rule check is never hidden
    assert "Regel-Check" in body
    assert "Nicht bestanden" in body
    assert "R21" in body
    assert "Keine Diagnoseliste" in body
    # templates in context with a link
    assert "Verwendete Vorlagen" in body
    assert '/app/vorlagen/Atherom.md' in body
    # document-type selector, default automatic
    assert 'id="doc_type"' in body and "Automatisch erkennen" in body
    # DOCX demoted to an optional secondary menu
    assert "DOCX mit Briefkopf herunterladen (optional)" in body


def test_editor_green_rule_check_when_clean(client, monkeypatch):
    register(client)
    monkeypatch.setattr(
        brain_bridge,
        "check_rules",
        lambda text, doc_type, dictation="": {
            "source": "methode", "available": True, "clean": True, "findings": [], "rules_total": 67,
        },
    )
    monkeypatch.setattr(pipeline_generate, "generate_letter", fake_generate())
    patient_id = create_patient(client)
    letter_id = create_letter(client, patient_id)
    client.post(f"/app/briefe/{letter_id}/erzeugen", data={"csrf_token": csrf(client), "dictation": "Text", "doc_type": "auto"})

    body = client.get(f"/app/briefe/{letter_id}").text
    assert "Regeln geprüft (R1–R67)" in body
    assert "is-clean" in body


def test_editor_empty_retrieval_offers_proposal(client, monkeypatch):
    register(client)
    monkeypatch.setattr(brain_bridge, "search_templates", lambda text, limit=5: [])
    monkeypatch.setattr(
        brain_bridge,
        "check_rules",
        lambda text, doc_type, dictation="": {
            "source": "portal", "available": True, "clean": True, "findings": [], "rules_total": 67,
        },
    )
    monkeypatch.setattr(pipeline_generate, "generate_letter", fake_generate())
    patient_id = create_patient(client)
    letter_id = create_letter(client, patient_id)
    client.post(f"/app/briefe/{letter_id}/erzeugen", data={"csrf_token": csrf(client), "dictation": "Text", "doc_type": "auto"})

    body = client.get(f"/app/briefe/{letter_id}").text
    assert "Keine Vorlage gefunden" in body
    assert "Vorlage vorschlagen" in body


def test_editor_explicit_document_type_is_persisted(client, monkeypatch):
    register(client)
    monkeypatch.setattr(
        brain_bridge,
        "detect_type",
        lambda text, explicit=None: {
            "key": brain_bridge.resolve_explicit_type(explicit),
            "label": "Zusammenfassung",
            "reason": "Von Ihnen gewählt.",
            "explicit": brain_bridge.resolve_explicit_type(explicit) != "auto",
        },
    )
    monkeypatch.setattr(pipeline_generate, "generate_letter", fake_generate())
    patient_id = create_patient(client)
    letter_id = create_letter(client, patient_id)
    client.post(
        f"/app/briefe/{letter_id}/erzeugen",
        data={"csrf_token": csrf(client), "dictation": "Kurzbericht.", "doc_type": "zusammenfassung"},
    )

    db = SessionLocal()
    try:
        assert db.get(Letter, letter_id).template_id == "zusammenfassung"
    finally:
        db.close()
    assert "Zusammenfassung" in client.get(f"/app/briefe/{letter_id}").text


def test_editor_real_rule_check_renders_a_state(client):
    """Without monkeypatching the checker the block renders either green or amber — never hidden."""
    register(client)
    patient_id = create_patient(client)
    letter_id = create_letter(client, patient_id)
    client.post(
        f"/app/briefe/{letter_id}/erzeugen",
        data={"csrf_token": csrf(client), "dictation": "Seit drei Wochen Rückenschmerzen ohne Ausstrahlung.", "doc_type": "auto"},
    )
    body = client.get(f"/app/briefe/{letter_id}").text
    assert "Regel-Check" in body
    assert "Regeln geprüft (R1–R" in body or "Nicht bestanden" in body

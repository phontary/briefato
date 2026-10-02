"""Chat portal (``/app/chat``) tests — self-triage, one clarifying question, one evolving letter.

Run:
    cd /workspace/briefato && BRIEFATO_LLM_MOCK=true .venv/bin/python -m pytest app/tests/test_chat_portal.py -q
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

TMP = tempfile.mkdtemp(prefix="briefato-chat-test-")
os.environ["BRIEFATO_DATA_DIR"] = TMP
os.environ["BRIEFATO_DB_URL"] = f"sqlite:///{Path(TMP) / 'chat.db'}"
os.environ["BRIEFATO_LLM_MOCK"] = "true"
os.environ["BRIEFATO_SECRET_KEY"] = "test-secret-chat"
os.environ.setdefault("BRIEFATO_ENV", "dev")

import pytest  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from briefato.config import get_settings  # noqa: E402
from briefato.db import Base, SessionLocal, engine  # noqa: E402
from briefato.main import app  # noqa: E402
from briefato.models import ChatMessage, ChatThread, Letter  # noqa: E402
from briefato.pipeline import generate as pipeline_generate  # noqa: E402
from briefato.pipeline import providers as pipeline_providers  # noqa: E402

PASSWORD = "geheim-1234"

# A dictation with a strong, unambiguous order term -> operationsbericht (confidence 0.85).
OP_DICTATION = (
    "OP-Bericht: 54-jaehrige Patientin, laparoskopische Cholezystektomie bei "
    "Cholezystolithiasis. Indikation: rezidivierende rechtsseitige Oberbauchschmerzen. "
    "Zugang: laparoskopisch, Vier-Trokar-Technik. Kernbefund: chronisch entzuendete, "
    "wandverdickte Gallenblase. Massnahmen: praeparierte und durchtrennte Strukturen, "
    "Bergung ueber Nabel. Drainagen: Lasche Unterbauch rechts. "
    "Standarddetails aus Referenz ergaenzen."
)

# A short, order-only input: triage has no signal, confidence 0.4 -> genuinely ambiguous.
AMBIGUOUS = "Bitte einen Brief."


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


# --------------------------------------------------------------------------- helpers


def csrf(client: TestClient) -> str:
    if not client.cookies.get("briefato_csrf"):
        client.get("/anmelden")
    return client.cookies.get("briefato_csrf")


def csrf_data(client: TestClient) -> dict:
    return {"csrf_token": csrf(client)}


def register(client: TestClient, email: str = "chat@example.de") -> None:
    response = client.post(
        "/registrieren",
        data={**csrf_data(client), "email": email, "password": PASSWORD,
              "full_name": "Dr. Chat", "practice_name": "Praxis Chat"},
    )
    assert response.status_code == 303, response.text


def create_patient(client: TestClient, last_name: str = "Muster", first_name: str = "Max") -> str:
    response = client.post(
        "/app/patienten/neu",
        data={**csrf_data(client), "last_name": last_name, "first_name": first_name, "city": "Stadt"},
    )
    assert response.status_code == 303, response.text
    return response.headers["location"].split("/app/patienten/")[1].split("?")[0]


def send(client: TestClient, message: str, patient_id: str = "", thread_id: str = "", **extra):
    data = {**csrf_data(client), "message": message}
    if patient_id:
        data["patient_id"] = patient_id
    if thread_id:
        data["thread_id"] = thread_id
    data.update(extra)
    return client.post("/app/chat", data=data)


def only_thread() -> ChatThread:
    db = SessionLocal()
    try:
        thread = db.query(ChatThread).one()
        db.expunge(thread)
        return thread
    finally:
        db.close()


def letters() -> list[Letter]:
    db = SessionLocal()
    try:
        return db.query(Letter).all()
    finally:
        db.close()


def candidate_buttons(html: str) -> list[str]:
    return re.findall(r'name="doc_type" value="([^"]+)"', html)


# --------------------------------------------------------------------------- page


def test_chat_page_renders_idle_composer(client):
    register(client)
    response = client.get("/app/chat")
    assert response.status_code == 200
    assert "data-chat" in response.text
    assert "chat--idle" in response.text
    # a real form with a labelled textarea, Enter-friendly and JS-free usable
    assert 'data-chat-form' in response.text
    assert 'action="/app/chat"' in response.text
    assert 'id="chat-message"' in response.text
    assert 'name="message"' in response.text
    assert 'for="chat-message"' in response.text
    assert "data-chat-input" in response.text
    assert "data-chat-composer" in response.text
    # one rotating capability line above the composer, rendered as sentences
    assert "data-chat-cap" in response.text
    assert response.text.count("data-chat-sentence") == 11
    for phrase in ("Arztbrief", "Attest", "Befund", "Entlassbrief", "OP-Bericht",
                   "Entlassmedikationsplan", "Pflegebericht", "Zusammenfassung",
                   "Verlegungsbericht", "Ablehnungsbogen", "KV-Nachweis"):
        assert phrase in response.text, phrase
    # the alternative entry is still offered
    assert 'href="/app/neu"' in response.text


def test_chat_requires_login(client):
    response = client.get("/app/chat")
    assert response.status_code == 303
    assert response.headers["location"].startswith("/anmelden")
    # a POST with a valid CSRF token but no session is redirected to the login page
    client.get("/anmelden")
    response = client.post("/app/chat", data={"csrf_token": csrf(client), "message": "x"})
    assert response.status_code == 303
    assert response.headers["location"].startswith("/anmelden")


def test_chat_post_requires_csrf(client):
    register(client)
    response = client.post("/app/chat", data={"message": "Bitte einen Brief."})
    assert response.status_code == 403


def test_chat_assets_encode_focus_fade_and_rotating_line(client):
    css = client.get("/assets/css/app.css")
    assert css.status_code == 200
    body = css.text
    assert ".is-chat-focus" in body
    assert ".chat-cap-sentence" in body
    assert ".chat-composer" in body
    assert "@keyframes chat-cap-in" in body
    assert "prefers-reduced-motion" in body

    js = client.get("/assets/js/app.js")
    assert js.status_code == 200
    script = js.text
    assert "data-chat-composer" in script
    assert "is-chat-focus" in script          # focus fade on/off
    assert "2500" in script                    # rotation cadence
    assert "data-chat-input" in script         # Enter sends
    assert "prefReducedMotion" in script       # rotation off under reduced motion


# --------------------------------------------------------------------------- self-triage


def test_dictation_produces_letter_with_correct_triage_type(client):
    register(client)
    patient_id = create_patient(client)
    response = send(client, OP_DICTATION, patient_id=patient_id)
    assert response.status_code == 200, response.text

    # the plain-text result with copy action, rule-check line, templates and editor link
    assert "Text kopieren" in response.text
    assert 'data-copy-target="#chat-letter-' in response.text
    assert "Regel-Check" in response.text
    assert "Verwendete Vorlagen" in response.text

    rows = letters()
    assert len(rows) == 1, "exactly one letter for one turn"
    letter = rows[0]
    assert letter.template_id == "operationsbericht", letter.template_id
    assert letter.kind == "arztbrief"
    assert f'href="/app/briefe/{letter.id}"' in response.text

    thread = only_thread()
    assert thread.letter_id == letter.id
    assert thread.doc_type == "operationsbericht"
    assert thread.status == "active"


def test_ambiguous_input_asks_one_question_with_candidates_and_no_letter(client):
    register(client)
    patient_id = create_patient(client)
    response = send(client, AMBIGUOUS, patient_id=patient_id)
    assert response.status_code == 200, response.text

    assert "Welche Dokumentart" in response.text
    buttons = candidate_buttons(response.text)
    assert len(buttons) == 3, buttons
    assert buttons[0] == "arztbrief"
    # no letter yet, and none of the letter-only affordances
    assert letters() == []
    assert "Text kopieren" not in response.text
    assert "chat-letter-" not in response.text

    db = SessionLocal()
    try:
        assert db.query(ChatMessage).filter_by(kind="question").count() == 1
        assert db.query(ChatThread).count() == 1
    finally:
        db.close()

    # the question is persisted: reopening the case shows it again
    thread = only_thread()
    reopened = client.get(f"/app/chat?thread={thread.id}")
    assert reopened.status_code == 200
    assert "Welche Dokumentart" in reopened.text


def test_choice_generates_letter_and_followup_refines_the_same_one(client):
    register(client)
    patient_id = create_patient(client)
    send(client, AMBIGUOUS, patient_id=patient_id)
    thread = only_thread()

    chosen = client.post(
        "/app/chat/wahl",
        data={**csrf_data(client), "thread_id": thread.id, "patient_id": patient_id,
              "doc_type": "arztbrief"},
    )
    assert chosen.status_code == 200, chosen.text
    rows = letters()
    assert len(rows) == 1
    letter_id = rows[0].id
    assert f'id="chat-letter-{letter_id}"' in chosen.text

    followed = send(client, "kuerzer", patient_id=patient_id, thread_id=thread.id)
    assert followed.status_code == 200, followed.text
    rows = letters()
    assert len(rows) == 1, "a follow-up must not create a second letter"
    assert rows[0].id == letter_id

    db = SessionLocal()
    try:
        kinds = [m.kind for m in db.query(ChatMessage).order_by(ChatMessage.created_at, ChatMessage.id)]
        assert kinds.count("letter") == 2, kinds
        assert "dictation" in kinds and "choice" in kinds and "followup" in kinds
        assert db.query(ChatThread).count() == 1
    finally:
        db.close()

    reopened = client.get(f"/app/chat?thread={thread.id}")
    assert reopened.status_code == 200
    assert "kuerzer" in reopened.text


# --------------------------------------------------------------------------- isolation


def test_tenant_isolation_on_chat_routes(client):
    register(client, email="owner@example.de")
    patient_id = create_patient(client)
    send(client, OP_DICTATION, patient_id=patient_id)
    thread = only_thread()
    letter_id = letters()[0].id

    other = TestClient(app, follow_redirects=False)
    other.post("/registrieren", data={**csrf_data(other), "email": "other@example.de",
                                      "password": PASSWORD, "full_name": "Other"})

    assert other.get(f"/app/chat?thread={thread.id}").status_code == 404
    assert other.get(f"/app/briefe/{letter_id}").status_code == 404
    assert other.post("/app/chat", data={**csrf_data(other), "thread_id": thread.id,
                                         "message": "weiter"}).status_code == 404
    assert other.post("/app/chat/wahl", data={**csrf_data(other), "thread_id": thread.id,
                                              "doc_type": "arztbrief"}).status_code == 404
    # a foreign patient id is a 404, never a silent fallback
    assert other.post("/app/chat", data={**csrf_data(other), "patient_id": patient_id,
                                         "message": OP_DICTATION}).status_code == 404


# --------------------------------------------------------------------------- pseudonymisation


def test_pseudonymisation_asserted_before_provider_call(client, monkeypatch):
    register(client)
    # Uncommon names so that a substring collision (e.g. "Muster" in "Musterbriefe")
    # cannot create a false positive.
    patient_id = create_patient(client, last_name="Hinterhuber", first_name="Kunigunde")

    class Spy:
        def __init__(self, inner):
            self.inner = inner
            self.calls: list[tuple[str, str]] = []

        def generate(self, system, user, **kwargs):
            self.calls.append((system, user))
            return self.inner.generate(system, user, **kwargs)

    spy = Spy(pipeline_providers.get_provider(get_settings()))
    monkeypatch.setattr(pipeline_generate, "get_provider", lambda settings: spy)

    dictation = (
        "OP-Bericht für Frau Kunigunde Hinterhuber: laparoskopische Cholezystektomie bei "
        "Cholezystolithiasis, Indikation rezidivierende Oberbauchschmerzen, Zugang "
        "laparoskopisch, Kernbefund wandverdickte Gallenblase, Drainage Unterbauch."
    )
    response = send(client, dictation, patient_id=patient_id)
    assert response.status_code == 200, response.text
    assert spy.calls, "the provider must have been called"
    assert 1 <= len(spy.calls) <= 2, "at most one call plus at most one repair retry"
    for _system, user in spy.calls:
        assert "Hinterhuber" not in user, "raw last name reached the provider prompt"
        assert "Kunigunde" not in user, "raw first name reached the provider prompt"
    assert any("{{LAST_NAME}}" in user for _system, user in spy.calls)
    assert any("{{FIRST_NAME}}" in user for _system, user in spy.calls)


# --------------------------------------------------------------------------- regressions


def test_no_inline_style_or_script_in_chat_templates(client):
    register(client)
    patient_id = create_patient(client)
    send(client, OP_DICTATION, patient_id=patient_id)
    thread = only_thread()
    for path in ("/app/chat", f"/app/chat?thread={thread.id}"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert "style=" not in response.text, path
        assert "<script>" not in response.text, path


def test_wizard_entry_still_available(client):
    register(client)
    response = client.get("/app/neu")
    assert response.status_code == 200
    assert "Was möchten Sie schreiben?" in response.text


def test_open_placeholders_are_marked_and_counted():
    """The method writes XXX where a value is unknown – the portal must make it visible."""
    from briefato.routes.chat import _mark_placeholders

    html, count = _mark_placeholders("Die Operation erfolgte am XXX in Intubationsnarkose.")
    assert count == 1
    assert '<mark class="ph-open"' in str(html)
    assert "XXX" in str(html)

    html, count = _mark_placeholders("Die Operation erfolgte am 23.09.2026.")
    assert count == 0
    assert "XXX" not in str(html)

    # letter text stays escaped, and XXX inside a word is not treated as a placeholder
    html, count = _mark_placeholders("<script>alert(1)</script> sowie XXXY")
    assert count == 0
    assert "<script>" not in str(html)

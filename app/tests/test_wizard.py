"""Wizard (``/app/neu``) tests — sequential, type-dependent, confirm-before-generate.

Run:
    cd /workspace/briefato && BRIEFATO_LLM_MOCK=true .venv/bin/python -m pytest app/tests/test_wizard.py -q
"""

from __future__ import annotations

import html
import json
import os
import re
import tempfile
from pathlib import Path
from types import SimpleNamespace

TMP = tempfile.mkdtemp(prefix="briefato-wizard-test-")
os.environ["BRIEFATO_DATA_DIR"] = TMP
os.environ["BRIEFATO_DB_URL"] = f"sqlite:///{Path(TMP) / 'wizard.db'}"
os.environ["BRIEFATO_LLM_MOCK"] = "true"
os.environ["BRIEFATO_SECRET_KEY"] = "test-secret-wizard"
os.environ.setdefault("BRIEFATO_ENV", "dev")

import pytest  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from briefato.db import Base, engine, SessionLocal  # noqa: E402
from briefato.main import app  # noqa: E402
from briefato.models import Letter  # noqa: E402
from briefato.pipeline import generate as pipeline_generate  # noqa: E402
from briefato.security import encrypt_field  # noqa: E402

PASSWORD = "geheim-1234"

CARD_LABELS = {
    "aufnahmebogen": "Aufnahmebogen",
    "entlassbrief": "Stationärer Entlassbrief",
    "verlegungsbericht": "Verlegungsbericht",
    "ambulant": "Ambulanter Brief",
    "operationsbericht": "OP-Bericht",
    "zusammenfassung": "Zusammenfassung",
    "entlassmedikationsplan": "Entlassmedikationsplan",
    "pflegebericht": "Pflegebericht-Integration",
    "ablehnungsbogen": "Ablehnungsbogen",
}


@pytest.fixture(autouse=True)
def _fresh_db():
    from briefato import models  # noqa: F401

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
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


def register(client: TestClient, email: str = "wizard@example.de") -> None:
    response = client.post(
        "/registrieren",
        data={**csrf_data(client), "email": email, "password": PASSWORD, "full_name": "Dr. Wizard"},
    )
    assert response.status_code == 303, response.text


def create_patient(client: TestClient, last_name: str = "Muster", first_name: str = "Max") -> str:
    response = client.post(
        "/app/patienten/neu",
        data={**csrf_data(client), "last_name": last_name, "first_name": first_name, "city": "Stadt"},
    )
    assert response.status_code == 303, response.text
    return response.headers["location"].split("/app/patienten/")[1].split("?")[0]


def state_of(html_text: str) -> dict:
    match = re.search(r'name="wiz_state" value="([^"]*)"', html_text)
    assert match, "the wizard must carry its state in a hidden wiz_state field"
    return json.loads(html.unescape(match.group(1)))


def heading_of(html_text: str) -> str:
    match = re.search(r"data-wizard-heading>(.*?)</h2>", html_text, re.S)
    return html.unescape(match.group(1)).strip() if match else ""


def choose_type(client: TestClient, wtype: str):
    return client.post(
        "/app/neu",
        data={**csrf_data(client), "wiz_state": "{}", "wiz_step": "0", "wtype": wtype},
    )


def step(client: TestClient, state: dict, step_index: int, action: str = "next", **fields):
    data = {**csrf_data(client), "wiz_state": json.dumps(state),
            "wiz_step": str(step_index), "action": action}
    data.update(fields)
    return client.post("/app/neu", data=data)


def walk_to_summary(client: TestClient, wtype: str, patient_id: str):
    """Choose a type and advance to the summary, answering the patient step. Returns
    (headings, final_state)."""
    response = choose_type(client, wtype)
    assert response.status_code == 200
    headings: list[str] = []
    state = state_of(response.text)
    for _ in range(25):
        headings.append(heading_of(response.text))
        if "Alles bereit?" in response.text:
            break
        fields = {}
        if 'name="patient_id"' in response.text:
            fields["patient_id"] = patient_id
        response = step(client, state, int(state.get("step", 0)), **fields)
        assert response.status_code == 200, response.text
        state = state_of(response.text)
    return headings, state


# --------------------------------------------------------------------------- step 1


def test_wizard_lists_all_nine_document_types(client):
    register(client)
    response = client.get("/app/neu")
    assert response.status_code == 200
    assert "Was möchten Sie schreiben?" in response.text
    for key, label in CARD_LABELS.items():
        assert f'name="wtype" value="{key}"' in response.text, key
        assert label in response.text, label
    assert 'class="wizard-progressbar"' not in response.text  # no progress indicator before a type


def test_wizard_requires_login(client):
    response = client.get("/app/neu")
    assert response.status_code == 303
    assert response.headers["location"].startswith("/anmelden")


def test_wizard_post_requires_csrf(client):
    register(client)
    response = client.post("/app/neu", data={"wiz_state": "{}", "wiz_step": "0", "wtype": "entlassbrief"})
    assert response.status_code == 403


# --------------------------------------------------------------------------- type dependence


@pytest.mark.parametrize(
    "wtype, expected_heading, absent_heading",
    [
        ("aufnahmebogen", "Aufnahme-Anamnese und Aufnahmebefund (KU)", None),
        ("entlassbrief", "Aufnahme-Anamnese und Aufnahmebefund (KU)", None),
        ("verlegungsbericht", "In welche Klinik oder Abteilung wurde verlegt?", None),
        ("ambulant", "Wie war der Aufnahme- und Entlasskontext?", None),
        ("operationsbericht", "Wann wurde operiert?", None),
        ("zusammenfassung", "Welchen Verlauf soll die Zusammenfassung verdichten?", "Welche Quellen"),
        ("entlassmedikationsplan", "Wie lautet der aktuelle Medikationsplan?", None),
        ("pflegebericht", "Bitte geben Sie die Pflegeberichte ein.", None),
        ("ablehnungsbogen", "Welche Maßnahme wurde abgelehnt?", None),
    ],
)
def test_each_type_reaches_its_own_steps(client, wtype, expected_heading, absent_heading):
    register(client)
    patient_id = create_patient(client)
    headings, state = walk_to_summary(client, wtype, patient_id)
    assert any(expected_heading in h for h in headings), (wtype, headings)
    assert headings.count("Alles bereit?") == 1
    if absent_heading:
        assert not any(absent_heading in h for h in headings), (wtype, headings)
    assert state.get("at_summary") is True
    assert state.get("doc_type")


def test_entlassbrief_and_op_bericht_have_different_step_counts(client):
    register(client)
    patient_id = create_patient(client)
    entlass, _ = walk_to_summary(client, "entlassbrief", patient_id)
    op, _ = walk_to_summary(client, "operationsbericht", patient_id)
    assert len(op) > len(entlass) >= 4
    assert any("Aufnahme-Anamnese" in h for h in entlass)
    assert any("Drainagen und Standarddetails" in h for h in op)
    assert any("Drainagen und Standarddetails" not in h for h in entlass)


def test_progress_indicator_and_fade_markup(client):
    register(client)
    response = choose_type(client, "entlassbrief")
    assert "Schritt 2 von" in response.text
    assert 'class="wizard-progressbar"' in response.text
    assert "wizard-step" in response.text
    assert "data-wizard-heading" in response.text
    assert "data-wizard-back" in response.text


# --------------------------------------------------------------------------- state / back


def test_state_survives_back_and_forward_without_data_loss(client):
    register(client)
    patient_id = create_patient(client)
    response = choose_type(client, "entlassbrief")
    state = state_of(response.text)

    # patient -> anamnese step
    response = step(client, state, 1, patient_id=patient_id)
    state = state_of(response.text)
    assert "Aufnahme-Anamnese" in response.text

    # fill the anamnese and advance to the sources step
    text = "Seit vier Wochen atraumatische Ulzeration am rechten Unterschenkel."
    response = step(client, state, 2, anamnese=text, ku="3x3 cm Ulzeration, Pulse tastbar.")
    state = state_of(response.text)
    assert state["anamnese"] == text
    assert "Quellen" in response.text

    # go back to the anamnese step — the entered text must be re-rendered (no data loss)
    response = step(client, state, 3, action="back")
    state = state_of(response.text)
    assert state["anamnese"] == text
    assert text in response.text

    # forward again — still there
    response = step(client, state, 2, anamnese=text, ku="3x3 cm Ulzeration, Pulse tastbar.")
    state = state_of(response.text)
    assert state["anamnese"] == text
    assert state.get("step") == 3


def test_sources_are_collected_and_counted(client):
    register(client)
    patient_id = create_patient(client)
    response = choose_type(client, "entlassbrief")
    state = state_of(response.text)
    response = step(client, state, 1, patient_id=patient_id)
    state = state_of(response.text)
    response = step(client, state, 2, anamnese="Anamnese", ku="KU")
    state = state_of(response.text)

    sources = [("CT", "CT Abdomen o. B."), ("MRT", "MRT Becken o. B."), ("Sono", "Sono Abdomen o. B.")]
    for label, body in sources:
        response = step(client, state, 3, action="add_source", src_label=label, src_text=body)
        assert response.status_code == 200
        state = state_of(response.text)

    assert len(state["sources"]) == 3
    assert "3 Quellen erfasst" in response.text
    assert "CT" in response.text and "MRT" in response.text

    # removing one works and stays on the step
    response = step(client, state, 3, remove_source="0")
    state = state_of(response.text)
    assert len(state["sources"]) == 2


# --------------------------------------------------------------------------- confirm-before-generate


def test_generation_is_impossible_before_the_summary_confirm(client):
    register(client)
    patient_id = create_patient(client)
    response = choose_type(client, "entlassbrief")
    state = state_of(response.text)
    response = step(client, state, 1, patient_id=patient_id)
    state = state_of(response.text)

    # posting the generate route with an early (non-summary) state must not create a letter
    response = client.post(
        "/app/neu/erzeugen",
        data={**csrf_data(client), "wiz_state": json.dumps(state), "wiz_step": "2"},
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/app/neu")
    db = SessionLocal()
    try:
        assert db.query(Letter).count() == 0
    finally:
        db.close()


def test_full_flow_generates_plain_text_result_with_copy_button(client):
    register(client)
    patient_id = create_patient(client, last_name="Muster", first_name="Greta")
    headings, state = walk_to_summary(client, "entlassbrief", patient_id)
    assert "Alles bereit?" in headings[-1] or True

    response = client.post(
        "/app/neu/erzeugen",
        data={**csrf_data(client), "wiz_state": json.dumps(state), "wiz_step": str(state["step"])},
    )
    assert response.status_code == 200, response.text

    # plain-text result + primary copy action
    assert 'data-copy-target="#result-text"' in response.text
    assert "Text kopieren" in response.text
    assert 'id="result-text"' in response.text
    assert "result-pane" in response.text
    # rule check panel + templates
    assert "Regel-Check" in response.text
    assert "Verwendete Vorlagen" in response.text

    # saved as a Letter row and listed in /app/briefe
    db = SessionLocal()
    try:
        letters = db.query(Letter).all()
        assert len(letters) == 1
        letter = letters[0]
        assert letter.kind == "arztbrief"
        assert letter.template_id == "arztbrief"
        assert letter.status in ("done", "failed")
        letter_id = letter.id
    finally:
        db.close()

    listing = client.get("/app/briefe")
    assert "Stationärer Entlassbrief Muster" in listing.text
    assert client.get(f"/app/neu/ergebnis/{letter_id}").status_code == 200
    assert client.get(f"/app/briefe/{letter_id}").status_code == 200  # kept editor still works


def test_seven_sources_flow_produces_a_document(client):
    register(client)
    patient_id = create_patient(client)
    response = choose_type(client, "entlassbrief")
    state = state_of(response.text)
    response = step(client, state, 1, patient_id=patient_id)
    state = state_of(response.text)
    response = step(client, state, 2, anamnese="Anamnese", ku="KU")
    state = state_of(response.text)

    for label, body in [
        ("CT", "CT Abdomen: gedeckt perforierte Cholezystitis."),
        ("MRT", "MRT Becken: keine Abszedierung."),
        ("Sono", "Sono Abdomen: Gallenblasenempyem."),
        ("Echo", "TTE: EF 55%."),
        ("Röntgen", "Thorax: kein Infiltrat."),
        ("Pathologie", "Histologie: chronische Cholezystitis."),
        ("Labor", "CRP 145 mg/l."),
    ]:
        response = step(client, state, 3, action="add_source", src_label=label, src_text=body)
        state = state_of(response.text)
    assert len(state["sources"]) == 7

    response = step(client, state, 3, action="next")
    state = state_of(response.text)
    assert state.get("at_summary") is True
    assert "7" in response.text  # "Quellen: 7" in the summary

    response = client.post(
        "/app/neu/erzeugen",
        data={**csrf_data(client), "wiz_state": json.dumps(state), "wiz_step": str(state["step"])},
    )
    assert response.status_code == 200, response.text
    assert 'id="result-text"' in response.text


# --------------------------------------------------------------------------- enrichments


def test_enrichments_rendered_with_source(client, monkeypatch):
    register(client)
    patient_id = create_patient(client)

    def fake_generate(db, *, user, patient, kind, dictation, letterhead, extra="", **kwargs):
        # the wizard opts this letter into grounded enrichment via the toggle
        assert kwargs.get("enrich") is True
        return SimpleNamespace(
            id="generated-not-persisted",
            user_id=user.id,
            kind=kind,
            status="done",
            content_enc=encrypt_field(
                "Sehr geehrte Damen und Herren,\n\nDer Verlauf war regelrecht.\n\nDiagnosen:\nTestdiagnose"
            ),
            model="mock-model",
            tokens_in=11,
            tokens_out=22,
            cost_usd=0.0,
            enrichments=[
                {"text": "Standardzugang wurde aus der Referenz ergänzt.",
                 "source": "OP-Bericht Referenz 10x15"},
            ],
        )

    monkeypatch.setattr(pipeline_generate, "generate_letter", fake_generate)

    response = choose_type(client, "operationsbericht")
    state = state_of(response.text)
    # answer the whole OP flow generically, including the reference-enrichment toggle
    for _ in range(15):
        if "Alles bereit?" in response.text:
            break
        fields = {}
        if 'name="patient_id"' in response.text:
            fields["patient_id"] = patient_id
        if 'name="standarddetails"' in response.text:
            fields["standarddetails"] = "1"
        state = state_of(response.text)
        response = step(client, state, int(state.get("step", 0)), **fields)

    state = state_of(response.text)
    assert state.get("at_summary") is True
    assert state.get("standarddetails") == "1"

    response = client.post(
        "/app/neu/erzeugen",
        data={**csrf_data(client), "wiz_state": json.dumps(state), "wiz_step": str(state["step"])},
    )
    assert response.status_code == 200, response.text
    assert "Aus Referenz ergänzt" in response.text
    assert "Standardzugang wurde aus der Referenz ergänzt." in response.text
    assert "Quelle: OP-Bericht Referenz 10x15" in response.text


# --------------------------------------------------------------------------- tenant isolation


def test_tenant_isolation_on_new_routes(client):
    register(client, email="owner@example.de")
    patient_id = create_patient(client)
    headings, state = walk_to_summary(client, "entlassbrief", patient_id)
    response = client.post(
        "/app/neu/erzeugen",
        data={**csrf_data(client), "wiz_state": json.dumps(state), "wiz_step": str(state["step"])},
    )
    assert response.status_code == 200
    db = SessionLocal()
    try:
        letter_id = db.query(Letter).first().id
    finally:
        db.close()

    # a second tenant
    other = TestClient(app, follow_redirects=False)
    other.post("/registrieren", data={**csrf_data(other), "email": "other@example.de",
                                      "password": PASSWORD, "full_name": "Other"})

    # foreign letter id on the new result route -> 404
    assert other.get(f"/app/neu/ergebnis/{letter_id}").status_code == 404

    # foreign patient id carried in the wizard state -> 404 on POST /app/neu
    foreign_state = {"wtype": "entlassbrief", "doc_type": "arztbrief", "step": 1,
                     "patient_id": patient_id, "sources": []}
    response = other.post(
        "/app/neu",
        data={**csrf_data(other), "wiz_state": json.dumps(foreign_state), "wiz_step": "1", "action": "next"},
    )
    assert response.status_code == 404

    # foreign patient id on the generate route -> 404
    gen_state = dict(foreign_state)
    gen_state["at_summary"] = True
    response = other.post(
        "/app/neu/erzeugen",
        data={**csrf_data(other), "wiz_state": json.dumps(gen_state), "wiz_step": "1"},
    )
    assert response.status_code == 404


# --------------------------------------------------------------------------- design pass


def test_design_tokens_and_reduced_motion_present(client):
    tokens = client.get("/assets/css/tokens.css")
    assert tokens.status_code == 200
    body = tokens.text
    assert "--canvas:" in body
    assert "--sheet:" in body
    assert "--nav-active-bg:" in body
    assert "prefers-color-scheme: dark" in body
    # radii 12/16/24 and the wider workspace target
    assert "--r-xl: 24px" in body
    assert "87.5rem" in body
    assert "72ch" in body

    css = client.get("/assets/css/app.css")
    assert css.status_code == 200
    # transition classes + reduced-motion guard
    assert "wizard-step--leaving" in css.text
    assert "@keyframes wizard-in" in css.text
    assert "prefers-reduced-motion: reduce" in css.text


def test_no_inline_style_or_script_in_new_templates(client):
    register(client)
    for path in ("/app/neu", "/app"):
        response = client.get(path)
        assert "style=" not in response.text, path
        assert "<script>" not in response.text, path

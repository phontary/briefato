"""Pipeline tests (WORKSTREAM-PIPELINE) — pseudonymisation, providers, DOCX, orchestration.

Offline only: ``BRIEFATO_LLM_MOCK=true`` and a temporary SQLite DB. Run with::

    cd /workspace/briefato && BRIEFATO_LLM_MOCK=true \\
        .venv/bin/python -m pytest app/tests/test_pipeline.py -q
"""

from __future__ import annotations

import os
import tempfile
import uuid
from datetime import date
from pathlib import Path
from types import SimpleNamespace

TMP = tempfile.mkdtemp(prefix="briefato-pipeline-test-")
os.environ.setdefault("BRIEFATO_DATA_DIR", TMP)
os.environ.setdefault("BRIEFATO_DB_URL", f"sqlite:///{Path(TMP) / 'pipeline.db'}")
os.environ.setdefault("BRIEFATO_LLM_MOCK", "true")
os.environ.setdefault("BRIEFATO_LLM_API_KEY", "super-secret-key-do-not-leak")
os.environ.setdefault("BRIEFATO_LLM_BASE_URL", "https://llm.example.test/v1")
os.environ.setdefault("BRIEFATO_SECRET_KEY", "test-secret")
os.environ.setdefault("BRIEFATO_ENV", "dev")

import httpx  # noqa: E402
import pytest  # noqa: E402
from docx import Document  # noqa: E402
from docx.shared import Cm  # noqa: E402

from briefato import security  # noqa: E402
from briefato.config import Settings  # noqa: E402
from briefato.db import SessionLocal, init_db  # noqa: E402
from briefato.models import AuditEvent, Generation, Letter, Patient, Subscription, User  # noqa: E402
from briefato.pipeline import generate as gen_mod  # noqa: E402
from briefato.pipeline.letterhead import render_docx  # noqa: E402
from briefato.pipeline.providers import (  # noqa: E402
    MockProvider,
    OpenAICompatProvider,
    PipelineProviderError,
)
from briefato.pipeline.pseudonym import Pseudonymizer  # noqa: E402


# --------------------------------------------------------------------------- fixtures


@pytest.fixture(scope="module", autouse=True)
def _db():
    init_db()
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _unique_suffix() -> str:
    return uuid.uuid4().hex[:10]


def _sample_patient(user_id: str) -> Patient:
    return Patient(
        user_id=user_id,
        first_name="Anna",
        last_name="Müller",
        birth_date=date(1974, 3, 2),
        sex="w",
        insurance="AOK",
        insurance_number="A123456789",
        street="Musterstraße 12",
        zip="10115",
        city="Berlin",
        phone="030 1234567",
        email="anna.mueller@example.de",
    )


def _sample_user() -> User:
    suffix = _unique_suffix()
    return User(
        email=f"arzt-{suffix}@praxis-test.de",
        password_hash="x",
        full_name="Dr. med. Weber",
        practice_name="Praxis Dr. Weber",
        street="Hauptstraße 1",
        zip="10115",
        city="Berlin",
        phone="030 5551234",
        tax_id="12/345/67890",
        ui_lang="de",
    )


def _doc_text(doc: Document) -> str:
    parts = [p.text for p in doc.paragraphs]
    for section in doc.sections:
        parts.extend(p.text for p in section.header.paragraphs)
        parts.extend(p.text for p in section.footer.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


class _SpyProvider:
    """Wraps the mock provider and records the exact prompts it received."""

    def __init__(self) -> None:
        self.system: str | None = None
        self.user: str | None = None
        self._inner = MockProvider()

    def generate(self, system: str, user: str, *, max_tokens: int = 2000, temperature: float = 0.2):
        self.system = system
        self.user = user
        return self._inner.generate(system, user, max_tokens=max_tokens, temperature=temperature)


class _BoomProvider:
    def generate(self, system: str, user: str, *, max_tokens: int = 2000, temperature: float = 0.2):
        raise PipelineProviderError(
            "Modellanbieter antwortete mit Status 500: internal error",
            status_code=500,
            provider="boom",
        )


def _test_settings(**overrides) -> Settings:
    values = dict(
        llm_api_key="super-secret-key-xyz",
        llm_base_url="https://llm.example.test/v1",
        llm_model="test-model",
        llm_timeout_s=5,
        llm_cost_in_per_1k=1.0,
        llm_cost_out_per_1k=2.0,
        llm_mock=False,
    )
    values.update(overrides)
    return Settings(**values)


# --------------------------------------------------------------------------- pseudonymiser


def test_pseudonymizer_roundtrip_german_text():
    patient = _sample_patient("u1")
    pz = Pseudonymizer.from_patient(patient)
    text = (
        "Patientin: Anna Müller, geb. am 02.03.1974, wohnhaft Musterstraße 12, 10115 Berlin. "
        "Versichertennummer A123456789, Telefon 030 1234567, E-Mail anna.mueller@example.de. "
        "Frau Müller stellte sich vor; der Name MÜLLER wird erneut genannt."
    )
    masked = pz.mask(text)

    for raw in ("Müller", "Anna", "02.03.1974", "A123456789", "Musterstraße 12", "030 1234567"):
        assert raw not in masked, f"raw value leaked: {raw}"
    assert "{{LAST_NAME}}" in masked
    assert "{{FIRST_NAME}}" in masked
    assert "{{BIRTH_DATE}}" in masked
    assert "{{INSURANCE_NUMBER}}" in masked
    assert "{{EMAIL}}" in masked
    # multiple occurrences, case-insensitive but uppercase token
    assert masked.count("{{LAST_NAME}}") == 3

    restored = pz.restore(masked)
    # Matching is case-insensitive, so an upper-cased occurrence is restored to the
    # canonical spelling of the stored value.
    assert restored == text.replace("MÜLLER", "Müller")

    fields = pz.masked_fields()
    assert fields["{{LAST_NAME}}"] == "Müller"
    assert fields["{{BIRTH_DATE}}"] == "02.03.1974"


def test_pseudonymizer_iso_birth_date_and_idempotency():
    pz = Pseudonymizer.from_patient(_sample_patient("u2"))
    text = "Der Patient, geb. 1974-03-02, wurde erneut vorgestellt."
    masked = pz.mask(text)
    assert "1974-03-02" not in masked
    assert "{{BIRTH_DATE}}" in masked
    # canonical German rendering is restored
    assert pz.restore(masked) == "Der Patient, geb. 02.03.1974, wurde erneut vorgestellt."

    # masking already-masked text must not corrupt the tokens
    assert pz.mask(masked) == masked
    assert pz.restore(pz.mask(masked)) == pz.restore(masked)


def test_pseudonymizer_empty_patient_is_noop():
    pz = Pseudonymizer.from_patient(None)
    assert pz.mask("Freitext ohne Patientendaten.") == "Freitext ohne Patientendaten."
    assert pz.restore("Freitext ohne Patientendaten.") == "Freitext ohne Patientendaten."
    assert pz.masked_fields() == {}


# --------------------------------------------------------------------------- providers


def test_provider_retries_429_then_succeeds():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, json={"error": {"message": "rate limited"}})
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Sehr geehrte Damen und Herren,"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                "model": "test-model",
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenAICompatProvider(_test_settings(), client=client, retry_backoff_s=0.0)
    result = provider.generate("system", "user")

    assert calls["n"] == 2, "expected exactly one retry after a 429"
    assert result.text == "Sehr geehrte Damen und Herren,"
    assert result.provider == "openai-compat"
    assert result.tokens_in == 10 and result.tokens_out == 5
    assert abs(result.cost_usd - (10 / 1000 * 1.0 + 5 / 1000 * 2.0)) < 1e-9
    assert result.latency_ms >= 0


def test_provider_permanent_500_raises_mapped_error_without_key():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500, text=("internal server error " * 60))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenAICompatProvider(_test_settings(), client=client, retry_backoff_s=0.0, max_retries=2)

    with pytest.raises(PipelineProviderError) as excinfo:
        provider.generate("system", "user")

    assert calls["n"] == 3, "expected initial call + 2 retries"
    assert excinfo.value.status_code == 500
    assert "500" in str(excinfo.value)
    assert len(str(excinfo.value)) < 500  # provider message truncated
    assert "super-secret-key-xyz" not in str(excinfo.value)


def test_provider_4xx_is_not_retried():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, json={"error": {"message": "bad request"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenAICompatProvider(_test_settings(), client=client, retry_backoff_s=0.0)

    with pytest.raises(PipelineProviderError) as excinfo:
        provider.generate("system", "user")

    assert calls["n"] == 1
    assert excinfo.value.status_code == 400


def test_provider_timeout_is_retried_then_mapped():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ReadTimeout("too slow", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenAICompatProvider(_test_settings(), client=client, retry_backoff_s=0.0)

    with pytest.raises(PipelineProviderError) as excinfo:
        provider.generate("system", "user")

    assert calls["n"] == 3
    assert "Zeitüberschreitung" in str(excinfo.value)
    assert excinfo.value.status_code is None


# --------------------------------------------------------------------------- letterhead


def test_render_docx_contains_date_subject_body_and_signature(tmp_path):
    letter_text = (
        "Sehr geehrte Damen und Herren,\n\n"
        "Betreff: Kardiologische Mitbeurteilung\n\n"
        "hiermit berichten wir über die o. g. Patientin.\n\n"
        "Mit freundlichen Grüßen\n\n"
        "Dr. med. Weber"
    )
    letterhead = {
        "practice_name": "Praxis Dr. Weber",
        "full_name": "Dr. med. Weber",
        "street": "Hauptstraße 1",
        "zip": "10115",
        "city": "Berlin",
        "phone": "030 5551234",
        "email": "kontakt@praxis-test.de",
        "date": "02.10.2026",
    }
    patient_ctx = {
        "last_name": "Müller",
        "first_name": "Anna",
        "birth_date": "02.03.1974",
        "insurance_number": "A123456789",
    }
    out_path = tmp_path / "arztbrief.docx"
    returned = render_docx(letter_text, letterhead, patient_ctx, out_path, "arztbrief")

    assert returned == out_path
    assert out_path.exists()

    doc = Document(str(out_path))  # must re-open cleanly
    text = _doc_text(doc)

    assert "02.10.2026" in text  # date
    assert "Kardiologische Mitbeurteilung" in text  # subject
    assert "hiermit berichten wir über die o. g. Patientin." in text  # body
    assert "Praxis Dr. Weber" in text  # signature area / footer
    assert "Müller, Anna" in text  # patient data block
    assert "A123456789" in text

    # A4, DIN-5008-style margins
    section = doc.sections[0]
    assert abs(section.page_width - Cm(21.0)) < 5000
    assert abs(section.left_margin - Cm(2.5)) < 5000

    # subject line is bold
    subject_paragraph = next(p for p in doc.paragraphs if p.text == "Kardiologische Mitbeurteilung")
    assert subject_paragraph.runs and subject_paragraph.runs[0].bold is True

    # body paragraphs use 1.15 line spacing
    body_paragraph = next(p for p in doc.paragraphs if p.text.startswith("hiermit berichten"))
    assert abs(float(body_paragraph.paragraph_format.line_spacing) - 1.15) < 1e-6


def test_render_docx_with_empty_letterhead_does_not_break(tmp_path):
    out_path = tmp_path / "empty.docx"
    render_docx("Sehr geehrte Damen und Herren,\n\nMit freundlichen Grüßen", {}, {}, out_path, "befund")
    assert out_path.exists()
    doc = Document(str(out_path))
    text = _doc_text(doc)
    assert "Sehr geehrte Damen und Herren" in text
    assert "Befund" in text  # synthesised subject fallback


# --------------------------------------------------------------------------- end to end


def test_generate_letter_end_to_end(db):
    user = _sample_user()
    db.add(user)
    db.commit()
    patient = _sample_patient(user.id)
    db.add(patient)
    subscription = Subscription(user_id=user.id, plan_code="starter", letters_quota=40, letters_used=0)
    db.add(subscription)
    db.commit()

    dictation = (
        "Patientin Anna Müller, geboren am 02.03.1974. "
        "Seit drei Tagen rechtsseitige Oberbauchschmerzen mit Ausstrahlung in die rechte Schulter. "
        "Sonographie: Cholelithiasis ohne Zeichen einer akuten Cholezystitis. "
        "Empfehlung: Vorstellung zur laparoskopischen Cholezystektomie."
    )
    letter = gen_mod.generate_letter(
        db,
        user=user,
        patient=patient,
        kind="arztbrief",
        dictation=dictation,
        letterhead={"practice_name": "Praxis Dr. Weber", "full_name": "Dr. med. Weber"},
    )

    assert letter.status == "done"
    assert letter.content_enc
    assert letter.dictation_enc != dictation

    restored = security.decrypt_field(letter.content_enc)
    assert "{{LAST_NAME}}" not in restored and "{{BIRTH_DATE}}" not in restored
    assert "Müller" in restored
    assert "02.03.1974" in restored
    assert security.decrypt_field(letter.dictation_enc) == dictation

    generation = db.query(Generation).filter_by(letter_id=letter.id).one()
    assert generation.status == "ok"
    assert generation.pseudonymised is True
    assert generation.tokens_in > 0 and generation.tokens_out > 0
    assert generation.provider == "mock"

    audit_events = db.query(AuditEvent).filter_by(event="letter.generated", target_id=letter.id).all()
    assert len(audit_events) == 1

    db.refresh(subscription)
    assert subscription.letters_used == 1


def test_generate_letter_prompt_contains_no_raw_identifiers(db, monkeypatch):
    user = _sample_user()
    db.add(user)
    db.commit()
    patient = _sample_patient(user.id)
    patient.last_name = "Zzyzx"
    patient.first_name = "Qwerta"
    patient.birth_date = date(1968, 11, 23)
    patient.insurance_number = "X999888777"
    patient.street = "Fantasieweg 5"
    patient.phone = "030 998877"
    patient.email = "qwert.zzyzx@example.de"
    db.add(patient)
    db.commit()

    spy = _SpyProvider()
    monkeypatch.setattr(gen_mod, "get_provider", lambda settings: spy)

    gen_mod.generate_letter(
        db,
        user=user,
        patient=patient,
        kind="arztbrief",
        dictation="Patientin Qwerta Zzyzx, geb. 23.11.1968, Fantasieweg 5, Tel. 030 998877.",
        letterhead={},
    )

    assert spy.system and spy.user
    captured = f"{spy.system}\n{spy.user}"
    for raw in ("Zzyzx", "Qwerta", "23.11.1968", "1968-11-23", "X999888777", "Fantasieweg 5", "998877"):
        assert raw.lower() not in captured.lower(), f"raw identifier leaked into prompt: {raw}"
    assert "{{LAST_NAME}}" in captured
    assert "{{BIRTH_DATE}}" in captured


def test_generate_letter_failure_marks_failed_and_keeps_quota(db, monkeypatch):
    user = _sample_user()
    db.add(user)
    db.commit()
    patient = _sample_patient(user.id)
    db.add(patient)
    subscription = Subscription(user_id=user.id, plan_code="starter", letters_quota=40, letters_used=2)
    db.add(subscription)
    db.commit()

    monkeypatch.setattr(gen_mod, "get_provider", lambda settings: _BoomProvider())

    with pytest.raises(gen_mod.PipelineGenerationError) as excinfo:
        gen_mod.generate_letter(
            db,
            user=user,
            patient=patient,
            kind="arztbrief",
            dictation="Patientin Anna Müller, geb. 02.03.1974.",
            letterhead={},
        )

    assert "500" in str(excinfo.value)
    assert "Müller" not in str(excinfo.value)  # error string is patient-data free

    letter = (
        db.query(Letter)
        .filter_by(user_id=user.id, patient_id=patient.id)
        .order_by(Letter.created_at.desc())
        .first()
    )
    assert letter is not None
    assert letter.status == "failed"
    assert letter.content_enc is None
    assert letter.error and "fehlgeschlagen" in letter.error.lower()

    db.refresh(subscription)
    assert subscription.letters_used == 2, "quota must not be incremented on failure"

    assert db.query(AuditEvent).filter_by(event="letter.failed", target_id=letter.id).count() == 1
    assert db.query(AuditEvent).filter_by(event="letter.generated", target_id=letter.id).count() == 0

"""Grounded enrichment / research tests (WORKSTREAM-ENGINE-V2).

No network: the web backend is exercised with an injected ``fetch`` callable and the
archive backend with stubbed retrieval/reader. Run with::

    cd /workspace/briefato && BRIEFATO_LLM_MOCK=true \\
        .venv/bin/python -m pytest app/tests/test_research.py -q
"""

from __future__ import annotations

import os
import tempfile
import uuid
from datetime import date
from pathlib import Path

TMP = tempfile.mkdtemp(prefix="briefato-research-test-")
os.environ.setdefault("BRIEFATO_DATA_DIR", TMP)
os.environ.setdefault("BRIEFATO_DB_URL", f"sqlite:///{Path(TMP) / 'research.db'}")
os.environ.setdefault("BRIEFATO_LLM_MOCK", "true")
os.environ.setdefault("BRIEFATO_SECRET_KEY", "test-secret-research")
os.environ.setdefault("BRIEFATO_ENV", "dev")

import pytest  # noqa: E402

from briefato.brain.retrieval import TemplateHit  # noqa: E402
from briefato.db import SessionLocal, init_db  # noqa: E402
from briefato.models import AuditEvent, Patient, Subscription, User  # noqa: E402
from briefato.pipeline import generate as gen_mod  # noqa: E402
from briefato.pipeline.providers import MockProvider  # noqa: E402
from briefato.research import (  # noqa: E402
    ArchiveEnricher,
    Enrichment,
    GroundedEnricher,
    NullEnricher,
    WebEnricher,
    enrich_if_enabled,
    filter_generic,
    get_research_provider,
    is_generic_statement,
)

DICTATION = (
    "Der Patient stellte sich mit rechtsseitigen Oberbauchschmerzen und Fieber vor. "
    "CT Abdomen zeigt eine Wandverdickung der Gallenblase, einzelne Konkremente. "
    "Laparoskopische Cholezystektomie mit Drainage wurde durchgeführt."
)


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


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("BRIEFATO_RESEARCH_BASE_URL", raising=False)
    monkeypatch.delenv("BRIEFATO_ENRICH_DEFAULT", raising=False)
    yield


# --------------------------------------------------------------------------- guardrail


def test_generic_statement_accepts_generic_standard_knowledge():
    assert is_generic_statement("Die Standardtechnik erfolgt über einen laparoskopischen Zugang.")
    assert is_generic_statement("Wundkontrolle und Fadenzug sind nach 10 bis 14 Tagen üblich.")


@pytest.mark.parametrize(
    "statement",
    [
        "Der Eingriff erfolgte am 03.09.2026.",  # date
        "Ibuprofen 800 mg bei Bedarf.",  # dosage
        "Gesicherte Diagnose K35.8.",  # ICD code
        "Bei diesem Patienten wurde eine Drainage eingelegt.",  # patient-possessive
        "kurz",  # too short
    ],
)
def test_generic_statement_rejects_patient_specific(statement):
    assert not is_generic_statement(statement)


def test_generic_statement_rejects_patient_identifiers():
    assert not is_generic_statement(
        "Die Technik nach Müller wird international verwendet.",
        patient_context={"last_name": "Müller"},
    )


def test_generic_statement_rejects_verbatim_dictation_copy():
    statement = "CT Abdomen zeigt eine Wandverdickung der Gallenblase, einzelne Konkremente."
    assert not is_generic_statement(statement, dictation=DICTATION)
    assert is_generic_statement(statement)  # generic on its own


def test_filter_generic_keeps_generic_and_counts_blocked():
    items = [
        Enrichment("Die Standardtechnik erfolgt über einen laparoskopischen Zugang.", "a.md"),
        Enrichment("Ibuprofen 800 mg bei Bedarf.", "b.md"),
        Enrichment("Die Standardtechnik erfolgt über einen laparoskopischen Zugang.", "c.md"),  # dup
    ]
    kept, blocked = filter_generic(items)
    assert [item.source for item in kept] == ["a.md"]
    assert blocked == 1  # the dosage; the duplicate is silently deduped


def test_null_enricher_returns_empty():
    assert NullEnricher().enrich(doc_type="arztbrief", context_text="x") == []


# --------------------------------------------------------------------------- archive


def _hit(file: str, score: float, reference_only: bool = False) -> TemplateHit:
    return TemplateHit(file=file, title=file, group="Test", score=score, reference_only=reference_only)


def test_archive_enricher_derives_from_templates_with_sources():
    templates = {
        "Referenz.md": (
            "## Diagnostik\n"
            "- Sonographie des Oberbauchs zur Beurteilung der Wanddicke\n"
            "## Therapie\n"
            "- Laparoskopische Cholezystektomie mit Standardzugang und Drainage\n"
            "- Sicherung der Gallenblase am Fundus\n"
            "## Nachsorge\n"
            "- Wundkontrolle und Fadenzug nach 10 bis 14 Tagen\n"
        ),
    }
    enricher = ArchiveEnricher(
        retrieve_fn=lambda query, limit=5: [_hit("Referenz.md", 9.0)],
        read_template_fn=templates.__getitem__,
    )
    items = enricher.enrich(doc_type="arztbrief", context_text="Cholezystitis", max_items=5)
    assert items, "the archive must yield reference statements"
    assert {item.source for item in items} == {"Referenz.md"}
    assert {item.origin for item in items} == {"archive"}
    assert any(item.kind == "materials" for item in items)
    assert any(item.kind == "follow_up" for item in items)


def test_archive_enricher_never_uses_reference_only_prose():
    def read(name: str) -> str:
        if name == "Licence.md":
            return "## Therapie\n- Lizenzierte Prosa, die niemals verwendet werden darf\n"
        return "## Therapie\n- Standardzugang mit Drainage\n"

    enricher = ArchiveEnricher(
        retrieve_fn=lambda query, limit=5: [_hit("Licence.md", 9.0, reference_only=True), _hit("Frei.md", 5.0)],
        read_template_fn=read,
    )
    items = enricher.enrich(doc_type="arztbrief", context_text="x", max_items=5)
    assert items and all(item.source == "Frei.md" for item in items)


def test_archive_enricher_survives_a_missing_template():
    def boom(_name: str) -> str:
        raise FileNotFoundError("gone")

    enricher = ArchiveEnricher(
        retrieve_fn=lambda query, limit=5: [_hit("Missing.md", 9.0)],
        read_template_fn=boom,
    )
    assert enricher.enrich(doc_type="arztbrief", context_text="x") == []


# --------------------------------------------------------------------------- web


def test_web_enricher_restricts_query_and_maps_sources():
    seen: dict[str, object] = {}

    def fetch(url: str, params: dict) -> dict:
        seen["url"] = url
        seen["q"] = params["q"]
        return {
            "results": [
                {
                    "url": "https://www.awmf.org/leitlinien/detail/x",
                    "content": "Die Standardtherapie ist die frühzeitige laparoskopische Cholezystektomie.",
                },
                {
                    "url": "https://pubmed.ncbi.nlm.nih.gov/123",
                    "content": "Der Patient erhielt Ibuprofen 800 mg am 03.09.2026.",
                },
            ]
        }

    enricher = WebEnricher("http://searxng:8080", fetch=fetch)
    items = enricher.enrich(doc_type="arztbrief", context_text="Cholezystitis Gallenblase", max_items=4)

    assert seen["url"] == "http://searxng:8080/search"
    query = str(seen["q"])
    for domain in ("awmf.org", "pubmed.ncbi.nlm.nih.gov", "doccheck.com", "msdmanuals.com", "leitlinien.de", "bfarm.de"):
        assert f"site:{domain}" in query
    assert [item.source for item in items] == ["https://www.awmf.org/leitlinien/detail/x"]
    assert items[0].origin == "web"


def test_web_enricher_without_base_url_makes_no_call():
    def fetch(url, params):  # pragma: no cover - must not be called
        raise AssertionError("no network call expected")

    assert WebEnricher("", fetch=fetch).enrich(doc_type="arztbrief", context_text="x") == []


def test_web_enricher_swallows_transport_errors():
    def fetch(url, params):
        raise RuntimeError("connection refused")

    assert WebEnricher("http://searxng:8080", fetch=fetch).enrich(doc_type="arztbrief", context_text="x") == []


# --------------------------------------------------------------------------- registry


def test_get_research_provider_attaches_web_only_when_configured(monkeypatch):
    provider = get_research_provider(None)
    assert isinstance(provider, GroundedEnricher)
    assert provider.web is None

    monkeypatch.setenv("BRIEFATO_RESEARCH_BASE_URL", "http://searxng:8080")
    provider = get_research_provider(None)
    assert provider.web is not None


def test_grounded_enricher_archive_first_then_web_supplements():
    class _Archive:
        def __init__(self) -> None:
            self.calls = 0

        def enrich(self, **kwargs):
            self.calls += 1
            return [Enrichment("Standardzugang mit Drainage.", "Referenz.md", kind="technique")]

    class _Web:
        def __init__(self) -> None:
            self.calls = 0

        def enrich(self, **kwargs):
            self.calls += 1
            return [Enrichment("Nachsorgekontrolle nach zwei Wochen üblich.", "https://x", kind="follow_up", origin="web")]

    archive, web = _Archive(), _Web()
    enricher = GroundedEnricher(archive=archive, web=web)
    items = enricher.enrich(doc_type="arztbrief", context_text="x", max_items=5)
    assert archive.calls == 1 and web.calls == 1
    assert {item.origin for item in items} == {"archive", "web"}


def test_grounded_enricher_skips_web_when_archive_is_full():
    class _Archive:
        def enrich(self, **kwargs):
            return [Enrichment(f"Standardhinweis {i}.", "Referenz.md") for i in range(6)]

    class _Web:
        def enrich(self, **kwargs):  # pragma: no cover - must not be reached
            raise AssertionError("web must not be consulted when the archive is full")

    items = GroundedEnricher(archive=_Archive(), web=_Web()).enrich(
        doc_type="arztbrief", context_text="x", max_items=6
    )
    assert len(items) == 6


def test_enrich_if_enabled_never_raises():
    class _Broken:
        def enrich(self, **kwargs):
            raise RuntimeError("boom")

    assert enrich_if_enabled(_Broken(), doc_type="arztbrief", context_text="x") == []


# --------------------------------------------------------------------------- end to end


class _StubResearch:
    def __init__(self, items):
        self.items = items
        self.calls = 0

    def enrich(self, **kwargs):
        self.calls += 1
        return list(self.items)


class _SpyProvider:
    def __init__(self) -> None:
        self._inner = MockProvider()
        self.prompts: list[str] = []

    def generate(self, system: str, user: str, *, max_tokens: int = 2000, temperature: float = 0.2):
        self.prompts.append(user)
        return self._inner.generate(system, user, max_tokens=max_tokens, temperature=temperature)


def _seed(db):
    user = User(
        email=f"arzt-{uuid.uuid4().hex[:10]}@research-test.de",
        password_hash="x",
        full_name="Dr. med. Weber",
        practice_name="Praxis Dr. Weber",
        ui_lang="de",
    )
    db.add(user)
    db.commit()
    patient = Patient(
        user_id=user.id,
        first_name="Anna",
        last_name="Müller",
        birth_date=date(1958, 4, 12),
        sex="w",
        insurance="AOK",
        insurance_number="A123456789",
        street="Musterstraße 12",
        zip="10115",
        city="Berlin",
        phone="030 1234567",
        email="anna.mueller@example.de",
    )
    db.add(patient)
    db.add(Subscription(user_id=user.id, plan_code="starter", letters_quota=40, letters_used=0))
    db.commit()
    return user, patient


def test_enriched_generation_audits_sources_and_blocks_patient_specific(db):
    user, patient = _seed(db)
    stub = _StubResearch(
        [
            Enrichment(
                "Die Standardtechnik erfolgt über einen laparoskopischen Zugang mit Drainage.",
                source="Gangraenose_Cholezystitis_CHE.md",
                kind="technique",
                origin="archive",
            ),
            Enrichment(
                "Die Patientin Anna erhielt 800 mg Ibuprofen am 03.09.2026.",
                source="https://example.org/patient",
                kind="standard",
                origin="web",
            ),
        ]
    )
    letter = gen_mod.generate_letter(
        db,
        user=user,
        patient=patient,
        kind="arztbrief",
        dictation=DICTATION,
        letterhead={},
        enrich=True,
        research_provider=stub,
    )
    assert stub.calls == 1
    assert letter.status == "done"

    enrichment = letter.last_check["enrichment"]
    assert enrichment["enabled"] is True
    assert enrichment["sources"] == ["Gangraenose_Cholezystitis_CHE.md"]
    assert enrichment["blocked"] >= 1
    assert enrichment["ui_note"] == "aus Referenz ergänzt – bitte prüfen"

    assert [item["source"] for item in letter.enrichments] == ["Gangraenose_Cholezystitis_CHE.md"]
    for item in letter.enrichments:
        assert "Anna" not in item["text"] and "800 mg" not in item["text"]

    audit = db.query(AuditEvent).filter_by(event="letter.enriched", target_id=letter.id).one()
    assert audit.meta_json["sources"] == ["Gangraenose_Cholezystitis_CHE.md"]
    assert audit.meta_json["statement_count"] == 1
    assert audit.meta_json["web_used"] is False


def test_enrichment_off_generates_without_the_audit_event(db):
    user, patient = _seed(db)
    stub = _StubResearch([Enrichment("Standardhinweis mit Drainage.", "Referenz.md")])
    letter = gen_mod.generate_letter(
        db,
        user=user,
        patient=patient,
        kind="arztbrief",
        dictation=DICTATION,
        letterhead={},
        enrich=False,
        research_provider=stub,
    )
    assert stub.calls == 0
    assert letter.status == "done"
    assert letter.enrichments == []
    assert letter.last_check["enrichment"]["enabled"] is False
    assert db.query(AuditEvent).filter_by(event="letter.enriched", target_id=letter.id).count() == 0


def test_default_enrich_comes_from_the_setting(db, monkeypatch):
    user, patient = _seed(db)
    monkeypatch.setenv("BRIEFATO_ENRICH_DEFAULT", "true")
    stub = _StubResearch(
        [Enrichment("Die Standardtechnik nutzt einen laparoskopischen Zugang.", "Referenz.md")]
    )
    letter = gen_mod.generate_letter(
        db,
        user=user,
        patient=patient,
        kind="arztbrief",
        dictation=DICTATION,
        letterhead={},
        research_provider=stub,
    )
    assert stub.calls == 1
    assert letter.enrichments, "the setting must enable enrichment by default"


def test_reference_knowledge_reaches_the_prompt(db, monkeypatch):
    user, patient = _seed(db)
    stub = _StubResearch(
        [Enrichment("Die Standardtechnik erfolgt über einen laparoskopischen Zugang.", "Referenz.md")]
    )
    spy = _SpyProvider()
    monkeypatch.setattr(gen_mod, "get_provider", lambda settings: spy)
    gen_mod.generate_letter(
        db,
        user=user,
        patient=patient,
        kind="arztbrief",
        dictation=DICTATION,
        letterhead={},
        enrich=True,
        research_provider=stub,
    )
    assert any("REFERENZWISSEN (generisch, nicht patientenbezogen)" in prompt for prompt in spy.prompts)
    assert any("laparoskopischen Zugang" in prompt for prompt in spy.prompts)
    # and the enrichment never carries a raw patient identifier into the prompt
    for prompt in spy.prompts:
        assert "Müller" not in prompt and "12.04.1958" not in prompt


def test_research_unavailable_still_produces_the_letter(db):
    user, patient = _seed(db)
    letter = gen_mod.generate_letter(
        db,
        user=user,
        patient=patient,
        kind="arztbrief",
        dictation=DICTATION,
        letterhead={},
        enrich=True,
        research_provider=NullEnricher(),
    )
    assert letter.status == "done"
    assert letter.enrichments == []

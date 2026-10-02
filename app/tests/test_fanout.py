"""Fan-out pipeline tests (WORKSTREAM-ENGINE-V2) — segmenter, routing, compression, weave.

Offline only: ``BRIEFATO_LLM_MOCK=true`` and a temporary SQLite DB. Run with::

    cd /workspace/briefato && BRIEFATO_LLM_MOCK=true \\
        .venv/bin/python -m pytest app/tests/test_fanout.py -q
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import tempfile

TMP = tempfile.mkdtemp(prefix="briefato-fanout-test-")
os.environ.setdefault("BRIEFATO_DATA_DIR", TMP)
os.environ.setdefault("BRIEFATO_DB_URL", f"sqlite:///{Path(TMP) / 'fanout.db'}")
os.environ.setdefault("BRIEFATO_LLM_MOCK", "true")
os.environ.setdefault("BRIEFATO_SECRET_KEY", "test-secret-fanout")
os.environ.setdefault("BRIEFATO_ENV", "dev")

import pytest  # noqa: E402

from briefato.db import SessionLocal, init_db  # noqa: E402
from briefato.models import AuditEvent, Patient, Subscription, User  # noqa: E402
from briefato.pipeline import fanout, routing, segmenter  # noqa: E402
from briefato.pipeline import generate as gen_mod  # noqa: E402
from briefato.pipeline.prompts import COMPRESSION_TASK, SEGMENT_TYPE_LINE, WEAVE_TASK  # noqa: E402
from briefato.pipeline.providers import LLMResult, MockProvider, PipelineProviderError  # noqa: E402
from briefato.brain.prompt_assembly import build_compression_prompt, build_weave_prompt  # noqa: E402
from briefato.brain.rule_checker import check as rule_check  # noqa: E402

BASE_ENV = {"BRIEFATO_MAX_PARALLEL": "", "BRIEFATO_FANOUT_THRESHOLD": ""}


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
    for key, value in BASE_ENV.items():
        if value:
            monkeypatch.setenv(key, value)
        else:
            monkeypatch.delenv(key, raising=False)
    yield


# --------------------------------------------------------------------------- fixtures

# Every source type the segmenter must recognise, one block each (18 headings).
ALL_TYPES_FIXTURE = """Aufnahme-Anamnese:
Seit zwei Tagen Unterbauchschmerzen und Fieber.

Röntgen-Thorax:
Kein Infiltrat.

CT Abdomen:
Wandverdickung der Sigma-Schlinge.

MRT Becken:
Keine Abszedierung.

Sonographie Abdomen:
Freie Fluessigkeit gering.

Echokardiographie:
EF 55 Prozent.

ÖGD:
PE aus dem Antrum entnommen.

Koloskopie:
Sigma entzuendlich veraendert.

Endosonographie:
Keine Infiltration.

OP-Bericht:
Laparoskopische Sigmaresektion.

Pathologie:
Akute Divertikulitis.

Diabetologie:
HbA1c 7,8 Prozent.

Pflegebericht:
Wundverhaeltnisse reizlos.

Visite:
Kostaufbau problemlos.

Labor:
CRP 187 mg/l.

Konsil:
Internistisches Konsil angefordert.

Diagnosen:
Akute Sigmadivertikulitis

ambulante Therapieempfehlungen nach der Entlassung:
Wundkontrolle beim Hausarzt.
"""

# A realistic 14-source KIS export (with form-label noise) for the end-to-end test.
REALISTIC_FIXTURE = """KIS-Export Unfallkrankenhaus Mitte
Pat.-Nr: 4711/26   Fall-Nr: 2026-0914
Aufnahme-Anamnese und KU:
Der 68-jaehrige Patient stellte sich mit seit zwei Tagen bestehenden rechtsseitigen Oberbauchschmerzen, Nausea und Fieber vor. Wir nahmen den Pat. zur weiteren Diagnostik bzw. Schmerztherapie stationaer auf. KU: Druckschmerz im rechten Oberbauch mit lokalem Abwehrspannungszeichen, kein Ikterus.

Labor:
CRP 187 mg/l, Leukozyten 17,4/nl, Bilirubin 1,2 mg/dl, Kreatinin 1,1 mg/dl.
Seite 1/9

CT Abdomen:
Wandverdickung der Gallenblase mit pericholezystaler Fettgewebestreifung, einzelne Konkremente. Kein Abszess, keine freie Luft. Gedeckt perforierte Cholezystitis.

Sonographie Abdomen:
Echoarmer Gallenblaseninhalt ohne Konkremente, Wandverdickung. Freie Fluessigkeit gering.

Röntgen-Thorax:
Kein Infiltrat, Herzgroesse normwertig. Nebenbefund: geringe linksseitige Pleuraergussbildung.

Koloskopie:
Unauffaellige Schleimhaut bis zum Coecum. PE aus dem Colon transversum entnommen. Die Histologie steht noch aus.

Endosonographie:
Konkrement im Ductus choledochus, keine Infiltration. Histologie steht aus.

OP-Bericht:
Indikation: Akute gedeckt perforierte Cholezystitis. Laparoskopischer Zugang, Calot-Dreieck praepariert, Cholezystektomie anterograd, Drainage in das Foramen Winslow eingelegt.

Pathologie:
Histologie: chronisch-fibrosierende Cholezystitis ohne Anhalt fuer Malignitaet.

Diabetologie:
BZ-Werte zwischen 140 und 220 mg/dl, HbA1c 7,8 Prozent, Insulin angepasst.

Pflegebericht:
Pat. zur Nacht versorgt, wirkt schlafend bei SK. Wundverhaeltnisse reizlos, Mobilisation an den Folgetagen zunehmend, Schmerzniveau ruecklaeufig.

Visite 12.09.2026:
Beschwerden deutlich ruecklaeufig, Kostaufbau problemlos, Stuhlgang vorhanden, Mobilisation gut. Verbandwechsel trocken.

Diagnosen:
Gedeckt perforierte Cholezystitis
Cholezystolithiasis
Z.n. laparoskopische Cholezytektomie
Diabetes mellitus Typ 2

ambulante Therapieempfehlungen nach der Entlassung:
Wundkontrolle beim Hausarzt. Blutzuckerselbstkontrolle fortsetzen.
"""


def _segment_named(fixture: str, expected: str) -> segmenter.Segment:
    for item in segmenter.segment(fixture):
        if item.segment_type == expected:
            return item
    raise AssertionError(f"no segment of type {expected!r}")


# --------------------------------------------------------------------------- segmenter


def test_segmenter_recognises_each_source_type():
    found = {item.segment_type for item in segmenter.segment(ALL_TYPES_FIXTURE)}
    expected = {
        "anamnese_ku", "roentgen", "ct", "mrt", "sono", "echo", "oegd", "kolo",
        "endosonographie", "op_bericht", "pathologie", "diabetologie", "pflegeberichte",
        "visiten", "labor", "konsile", "diagnosen", "therapie_empfehlung",
    }
    assert expected <= found, expected - found


def test_segmenter_realistic_fixture_yields_12_to_18_sources():
    segments = segmenter.segment(REALISTIC_FIXTURE)
    assert 12 <= len(segments) <= 18, [s.as_dict() for s in segments]
    assert all(item.confidence > 0 for item in segments)
    types = {item.segment_type for item in segments}
    assert {"anamnese_ku", "ct", "sono", "roentgen", "op_bericht", "pathologie",
            "pflegeberichte", "visiten", "labor", "diagnosen", "therapie_empfehlung"} <= types


def test_segmenter_drops_form_label_noise():
    segments = segmenter.segment(REALISTIC_FIXTURE)
    # the KIS header / Pat.-Nr / Seite lines must not become a Rohtext source.
    assert all(item.segment_type != "rohtext" for item in segments)
    joined = "\n".join(item.text for item in segments)
    assert "Pat.-Nr" not in joined and "Seite 1/9" not in joined


def test_segmenter_merges_adjacent_duplicate_labels():
    fixture = "Labor:\nCRP 187 mg/l.\nLabor:\nLeukozyten 17/nl.\nCT Abdomen:\nWandverdickung.\n"
    segments = segmenter.segment(fixture)
    labor = [item for item in segments if item.segment_type == "labor"]
    assert len(labor) == 1
    assert "CRP 187 mg/l" in labor[0].text and "Leukozyten 17/nl" in labor[0].text


def test_segmenter_marks_non_adjacent_duplicates():
    fixture = "Labor:\nCRP 187 mg/l.\nCT Abdomen:\nWandverdickung.\nLabor:\nLeukozyten 17/nl.\n"
    segments = segmenter.segment(fixture)
    labs = [item for item in segments if item.segment_type == "labor"]
    assert len(labs) == 2
    assert labs[1].duplicate_of == labs[0].index


def test_segmenter_missing_labels_falls_back_to_one_rohtext():
    segments = segmenter.segment("Freier Text ohne jede Ueberschrift. Nur ein Absatz Befund.")
    assert len(segments) == 1
    assert segments[0].segment_type == "rohtext"
    assert segments[0].confidence == 0.0


def test_segmenter_diagnosis_line_is_not_a_heading():
    fixture = "Diagnosen:\nDiabetes mellitus Typ 2\nAkute Cholezystitis\n"
    segments = segmenter.segment(fixture)
    assert len(segments) == 1
    assert segments[0].segment_type == "diagnosen"
    assert "Diabetes mellitus Typ 2" in segments[0].text


def test_segmenter_confidence_higher_for_label_with_inline_content():
    with_content = segmenter.segment("Labor: CRP 187 mg/l.")[0]
    without_content = segmenter.segment("Labor:\nCRP 187 mg/l.")[0]
    assert with_content.confidence > without_content.confidence


# --------------------------------------------------------------------------- routing


def test_route_fanout_above_five_stationary_sources():
    decision = routing.decide_route("arztbrief", 6)
    assert decision.route == routing.FANOUT and decision.is_fanout
    assert decision.ui_label == "Route: Fan-out (6 Quellen)"
    assert "> 5" in decision.reason


def test_route_single_pass_at_or_below_five_sources():
    for count in (0, 1, 5):
        decision = routing.decide_route("arztbrief", count)
        assert decision.route == routing.SINGLE_PASS, count
        assert f"({count} Quellen)" in decision.ui_label


def test_route_single_pass_for_non_stationary_even_with_many_sources():
    decision = routing.decide_route("operationsbericht", 9)
    assert decision.route == routing.SINGLE_PASS


def test_route_threshold_is_configurable(monkeypatch):
    monkeypatch.setenv("BRIEFATO_FANOUT_THRESHOLD", "10")
    assert routing.decide_route("arztbrief", 6).route == routing.SINGLE_PASS
    assert routing.decide_route("arztbrief", 11).route == routing.FANOUT


def test_route_honours_an_explicit_briefart_hint():
    decision = routing.decide_route("sonstiges", 7, briefart="verlegungsbrief")
    assert decision.route == routing.FANOUT


# --------------------------------------------------------------------------- mock compression / weave


def test_mock_provider_compresses_a_segment_deterministically_without_labels():
    provider = MockProvider()
    prompt = build_compression_prompt(
        doc_type="arztbrief",
        segment_type="ct",
        segment_text="CT Abdomen: Wandverdickung der Gallenblase. Kein Abszess, keine freie Luft. Normale Leber.",
    )
    assert COMPRESSION_TASK in prompt.user and SEGMENT_TYPE_LINE in prompt.user
    first = provider.generate(prompt.system, prompt.user).text
    second = provider.generate(prompt.system, prompt.user).text
    assert first == second and first
    assert "CT Abdomen:" not in first  # no category label survives
    assert "**" not in first and "#" not in first


def test_mock_provider_weaves_a_method_shaped_document():
    provider = MockProvider()
    compressed = [
        {"type": "anamnese_ku", "text": "Der Patient stellte sich mit Oberbauchschmerzen vor. Wir nahmen die Pat. zur weiteren Diagnostik bzw. Schmerztherapie stationär auf."},
        {"type": "ct", "text": "Wandverdickung der Gallenblase, kein Abszess."},
        {"type": "op_bericht", "text": "Akute Cholezystitis. Laparoskopischer Zugang, Cholezystektomie, Drainage eingelegt."},
        {"type": "diagnosen", "text": "Akute Cholezystitis\nZ.n. Cholezystektomie"},
        {"type": "therapie_empfehlung", "text": "Wundkontrolle beim Hausarzt."},
    ]
    prompt = build_weave_prompt(doc_type="arztbrief", compressed=compressed, letterhead={}, patient_ctx={})
    assert WEAVE_TASK in prompt.user
    text = provider.generate(prompt.system, prompt.user).text
    assert "Diagnosen:" in text and "Nebenerkrankungen:" in text
    assert "ambulante Therapieempfehlungen nach der Entlassung:" in text
    assert "stationär auf" in text
    # Z.n. line moved out of the Diagnosen list (R23)
    diag = text.split("Diagnosen:", 1)[1].split("Nebenerkrankungen:", 1)[0]
    assert "Z.n." not in diag
    assert rule_check(text, "arztbrief", "").ok


# --------------------------------------------------------------------------- engine


class _SleepProvider:
    """Mock compression/weave with a sleep so call overlap is observable."""

    def __init__(self, delay: float = 0.02) -> None:
        self._inner = MockProvider()
        self._delay = delay
        self._lock = threading.Lock()
        self.in_flight = 0
        self.peak = 0
        self.calls = 0

    def generate(self, system: str, user: str, *, max_tokens: int = 2000, temperature: float = 0.2):
        with self._lock:
            self.in_flight += 1
            self.calls += 1
            self.peak = max(self.peak, self.in_flight)
        try:
            time.sleep(self._delay)
            return self._inner.generate(system, user, max_tokens=max_tokens, temperature=temperature)
        finally:
            with self._lock:
                self.in_flight -= 1


def _fake_segments(count: int) -> list[SimpleNamespace]:
    return [
        SimpleNamespace(segment_type="labor", text=f"Befund Nummer {i}.", confidence=0.8, index=i)
        for i in range(count)
    ]


def test_compress_segments_never_exceeds_max_parallel():
    tracker = fanout.ConcurrencyTracker(3)
    provider = _SleepProvider(delay=0.03)
    results, stats = fanout.compress_segments(
        _fake_segments(12), provider=provider, doc_type="arztbrief", tracker=tracker, max_parallel=3
    )
    assert len(results) == 12
    assert all(item.ok for item in results)
    assert provider.peak <= 3
    assert stats["max_parallel"] == 3
    assert stats["compression_calls"] == 12
    assert tracker.peak <= 3


def test_compress_segments_cap_two():
    tracker = fanout.ConcurrencyTracker(2)
    provider = _SleepProvider(delay=0.03)
    _results, stats = fanout.compress_segments(
        _fake_segments(8), provider=provider, doc_type="arztbrief", tracker=tracker, max_parallel=2
    )
    assert provider.peak <= 2
    assert stats["max_parallel"] == 2


class _FlakyProvider:
    """Fails compression for chosen segment types (first attempt or permanently)."""

    def __init__(self, first_attempt_fail: set[str] | None = None, always_fail: set[str] | None = None) -> None:
        self._inner = MockProvider()
        self._first = set(first_attempt_fail or ())
        self._always = set(always_fail or ())
        self._seen: dict[str, int] = {}
        self._lock = threading.Lock()

    def generate(self, system: str, user: str, *, max_tokens: int = 2000, temperature: float = 0.2):
        import re

        match = re.search(r"Segmenttyp:\s*([a-z_]+)", user or "")
        seg_type = match.group(1) if match else None
        if seg_type is not None and (seg_type in self._always or seg_type in self._first):
            with self._lock:
                self._seen[seg_type] = self._seen.get(seg_type, 0) + 1
                attempt = self._seen[seg_type]
            if seg_type in self._always or attempt == 1:
                raise PipelineProviderError("Modellanbieter antwortete mit Status 500", status_code=500, provider="flaky")
        return self._inner.generate(system, user, max_tokens=max_tokens, temperature=temperature)


def test_compress_segments_retries_once_then_records_gap():
    tracker = fanout.ConcurrencyTracker(3)
    provider = _FlakyProvider(first_attempt_fail={"sono"}, always_fail={"labor"})
    segments = [
        SimpleNamespace(segment_type="sono", text="Sono Befund.", confidence=0.8, index=0),
        SimpleNamespace(segment_type="labor", text="CRP 187 mg/l.", confidence=0.8, index=1),
        SimpleNamespace(segment_type="ct", text="CT Befund.", confidence=0.8, index=2),
    ]
    results, stats = fanout.compress_segments(
        segments, provider=provider, doc_type="arztbrief", tracker=tracker, max_parallel=2
    )
    by_type = {item.segment_type: item for item in results}
    assert by_type["sono"].ok and by_type["sono"].attempts == 2  # retried once
    assert by_type["labor"].gap and by_type["labor"].attempts == 2  # retried, still failed
    assert by_type["ct"].ok
    assert stats["segments_failed"] == 1
    assert stats["gaps"][0]["type"] == "labor"


def _sample_user() -> User:
    suffix = uuid.uuid4().hex[:10]
    return User(
        email=f"arzt-{suffix}@fanout-test.de",
        password_hash="x",
        full_name="Dr. med. Weber",
        practice_name="Praxis Dr. Weber",
        ui_lang="de",
    )


def _seed(db):
    user = _sample_user()
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


def test_fanout_end_to_end_reports_route_segments_and_calls(db):
    user, patient = _seed(db)
    letter = gen_mod.generate_letter(
        db,
        user=user,
        patient=patient,
        kind="arztbrief",
        dictation=REALISTIC_FIXTURE,
        letterhead={"practice_name": "Praxis Dr. Weber"},
        max_parallel=3,
    )
    assert letter.status == "done"
    last = letter.last_check
    assert last["route"]["route"] == routing.FANOUT
    assert last["route"]["ui_label"] == "Route: Fan-out (14 Quellen)"
    assert last["source_count"] == 14
    compression = last["compression"][0]
    assert compression["segments_total"] == 14
    assert compression["segments_ok"] == 14 and compression["segments_failed"] == 0
    assert compression["max_parallel"] == 3
    # 14 compressions + 1 weave (the mock draft is checker-clean, no retry)
    assert last["model_calls"] == 15
    assert 1 <= last["max_concurrency"] <= 3
    assert all(check["ok"] for check in last["checks"])

    audit = db.query(AuditEvent).filter_by(event="letter.generated", target_id=letter.id).one()
    assert audit.meta_json["route"] == routing.FANOUT
    assert audit.meta_json["source_count"] == 14
    assert audit.meta_json["model_calls"] >= 15
    assert audit.meta_json["compression_gaps"] == []


def test_fanout_partial_failure_is_reported_not_silently_dropped(db, monkeypatch):
    user, patient = _seed(db)
    monkeypatch.setattr(
        gen_mod, "get_provider", lambda settings: _FlakyProvider(always_fail={"labor"})
    )
    letter = gen_mod.generate_letter(
        db,
        user=user,
        patient=patient,
        kind="arztbrief",
        dictation=REALISTIC_FIXTURE,
        letterhead={},
    )
    assert letter.status == "done"
    compression = letter.last_check["compression"][0]
    assert compression["segments_failed"] == 1
    gaps = [gap["type"] for gap in compression["gaps"]]
    assert gaps == ["labor"]

    audit = db.query(AuditEvent).filter_by(event="letter.generated", target_id=letter.id).one()
    assert audit.meta_json["compression_gaps"] == ["labor"]

    # the failed segment's distinctive content is genuinely absent from the document
    from briefato import security

    content = security.decrypt_field(letter.content_enc)
    assert "Bilirubin" not in content


def test_fanout_respects_max_parallel_env(db, monkeypatch):
    user, patient = _seed(db)
    monkeypatch.setenv("BRIEFATO_MAX_PARALLEL", "2")
    letter = gen_mod.generate_letter(
        db,
        user=user,
        patient=patient,
        kind="arztbrief",
        dictation=REALISTIC_FIXTURE,
        letterhead={},
    )
    assert letter.last_check["max_parallel"] == 2
    assert letter.last_check["max_concurrency"] <= 2


def test_single_pass_for_few_sources_is_unchanged(db):
    user, patient = _seed(db)
    letter = gen_mod.generate_letter(
        db,
        user=user,
        patient=patient,
        kind="arztbrief",
        dictation="Patient mit Oberbauchschmerzen, Sonographie zeigt eine Cholelithiasis ohne Cholezystitis.",
        letterhead={},
    )
    assert letter.status == "done"
    assert letter.last_check["route"]["route"] == routing.SINGLE_PASS
    assert letter.last_check["compression"] == []
    assert letter.last_check["model_calls"] in (1, 2)  # single pass (+ optional retry)


def test_triage_does_not_switch_on_a_source_heading(db):
    """A stationary multi-source export must not be re-triaged to a standalone OP-Bericht."""
    user, patient = _seed(db)
    letter = gen_mod.generate_letter(
        db,
        user=user,
        patient=patient,
        kind="arztbrief",
        dictation=REALISTIC_FIXTURE,
        letterhead={},
    )
    assert letter.kind == "arztbrief"
    assert letter.last_check["doc_type"] == "arztbrief"


def test_mock_provider_compression_prompts_carry_only_masked_text(db, monkeypatch):
    """Every fan-out prompt must be masked — no raw patient identifier may reach it."""
    user, patient = _seed(db)
    captured: list[str] = []

    class _Spy:
        def __init__(self) -> None:
            self._inner = MockProvider()

        def generate(self, system: str, user: str, *, max_tokens: int = 2000, temperature: float = 0.2):
            captured.append(user)
            return self._inner.generate(system, user, max_tokens=max_tokens, temperature=temperature)

    monkeypatch.setattr(gen_mod, "get_provider", lambda settings: _Spy())
    gen_mod.generate_letter(
        db,
        user=user,
        patient=patient,
        kind="arztbrief",
        dictation=REALISTIC_FIXTURE,
        letterhead={},
    )
    assert len(captured) >= 15  # 14 compressions + weave
    for prompt in captured:
        for raw in ("Müller", "Anna", "12.04.1958", "A123456789", "Musterstraße 12", "030 1234567"):
            assert raw.lower() not in prompt.lower(), raw
    assert any(COMPRESSION_TASK in prompt for prompt in captured)
    assert any(WEAVE_TASK in prompt for prompt in captured)


def test_resolve_max_parallel_defaults_and_clamps(monkeypatch):
    monkeypatch.delenv("BRIEFATO_MAX_PARALLEL", raising=False)
    assert fanout.resolve_max_parallel() == 3
    assert fanout.resolve_max_parallel(5) == 5
    assert fanout.resolve_max_parallel(0) == 1
    assert fanout.resolve_max_parallel(99) == 8

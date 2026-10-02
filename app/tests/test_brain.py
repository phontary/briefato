"""Brain tests (WORKSTREAM-BRAIN-WIRING) — loader, triage, retrieval, prompt, checker.

Offline only. Run with::

    cd /workspace/briefato && .venv/bin/python -m pytest app/tests/test_brain.py -q
"""

from __future__ import annotations

import re

import pytest

from briefato.brain import brain_loader, prompt_assembly, retrieval, rule_checker, triage
from briefato.brain.prompt_assembly import build_prompt
from briefato.brain.rule_checker import check
from briefato.brain.triage import DOC_TYPES, TriageDecision


# --------------------------------------------------------------------------- loader


def test_loader_finds_the_brain():
    status = brain_loader.status()
    assert brain_loader.kern_text().strip()
    assert len(brain_loader.rules()) == 67
    assert len(brain_loader.anti_pattern_lines()) == 25
    assert status["templates"] == 152
    assert status["playbooks"] == len(brain_loader.DOKUMENTTYPEN) == 9
    # every playbook is loadable
    for doc_type in brain_loader.DOKUMENTTYPEN:
        assert brain_loader.dokumenttyp_text(doc_type).strip()


def test_loader_missing_brain_fails_with_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("BRIEFATO_BRAIN_DIR", str(tmp_path / "does-not-exist"))
    brain_loader.clear_caches()
    try:
        with pytest.raises(brain_loader.BrainNotFound) as excinfo:
            brain_loader.kern_text()
        message = str(excinfo.value)
        assert "BRIEFATO_BRAIN_DIR" in message and "kern.md" in message
    finally:
        monkeypatch.delenv("BRIEFATO_BRAIN_DIR", raising=False)
        brain_loader.clear_caches()
    # and it recovers once the env override is gone
    assert brain_loader.kern_text()


def test_rule_parsing_has_ids_and_provenance():
    rules = {rule.id: rule for rule in brain_loader.rules()}
    assert set(rules) == {f"R{n}" for n in range(1, 68)}
    assert "Kein Markdown" in rules["R4"].text or "Markdown" in rules["R4"].text
    assert rules["R21"].provenance


# --------------------------------------------------------------------------- triage


@pytest.mark.parametrize(
    "dictation,explicit,expected",
    [
        ("Rohmaterial ohne expliziten Auftrag zur Aufnahme.", None, ("arztbrief",)),
        ("Bitte nur die Zusammenfassung des Verlaufs.", None, ("zusammenfassung",)),
        ("Bitte einen ausführlichen OP-Bericht.", None, ("operationsbericht",)),
        ("Ambulanter Eingriff, noch am OP-Tag entlassen.", None, ("ambulant",)),
        ("Dem Diktat sind Pflegeberichte beigefügt.", None, ("pflegebericht",)),
        ("Bitte den Medikationsplan für diesen Fall anpassen.", None, ("entlassmedikationsplan",)),
        ("Ablehnungsbogen Thieme Compliance bitte.", None, ("ablehnungsbogen",)),
        ("WBO / KV-Genehmigung als Nachweis.", None, ("weiterbildung-kv-nachweise",)),
        # explicit real type is honoured
        ("irgendein Rohtext", "zusammenfassung", ("zusammenfassung",)),
        # legacy kind without a brain playbook falls through to the dictation routing
        ("Bitte nur die Zusammenfassung.", "sonstiges", ("zusammenfassung",)),
        # explicit default Arztbrief still yields to a specific dictation order
        ("Bitte OP-Bericht.", "arztbrief", ("operationsbericht",)),
    ],
)
def test_triage_routing(dictation, explicit, expected):
    decision = triage.triage(dictation, explicit=explicit)
    assert isinstance(decision, TriageDecision)
    assert decision.doc_types == expected
    assert 0.0 <= decision.confidence <= 1.0
    assert decision.reason


def test_triage_combined_order_returns_both_documents():
    decision = triage.triage("Bitte OP-Bericht + Zusammenfassung aus demselben Material.")
    assert decision.doc_types == ("operationsbericht", "zusammenfassung")
    assert decision.combined is True
    assert decision.doc_type == "operationsbericht"


def test_triage_exposes_type_list_for_the_ui():
    options = triage.doc_type_options()
    values = [option["value"] for option in options]
    assert values == list(DOC_TYPES)
    assert all(option["label"] for option in options)


# --------------------------------------------------------------------------- retrieval


@pytest.mark.parametrize("query,expected", retrieval.SELFTEST_QUERIES)
def test_retrieval_top1_for_selftest_queries(query, expected):
    hits = retrieval.retrieve(query, limit=1)
    assert hits, f"no retrieval hit for {query!r}"
    top = hits[0]
    if expected == "Cholezystolithiasis.md":
        # This expected file is scrub-pending and must never be returned; the next
        # best match is still a biliary/gallbladder template.
        assert top.file not in retrieval.SCRUB_PENDING
        assert re.search(r"gallen|chole", top.file, re.IGNORECASE), top.file
    else:
        assert expected.lower() in top.file.lower(), f"{query!r} -> {top.file}"


@pytest.mark.parametrize("scrub_file", sorted(retrieval.SCRUB_PENDING))
def test_scrub_pending_templates_can_never_be_retrieved(scrub_file):
    # not available at all
    assert scrub_file not in {entry["file"] for entry in retrieval.available_templates()}
    # and not returned for any of the self-test queries
    for query, _ in retrieval.SELFTEST_QUERIES:
        assert scrub_file not in {hit.file for hit in retrieval.retrieve(query, limit=50)}
    # nor when the filename itself is the query
    stem = scrub_file[:-3].replace("_", " ")
    assert scrub_file not in {hit.file for hit in retrieval.retrieve(stem, limit=50)}


def test_licence_review_templates_are_marked_reference_only():
    flagged = retrieval.reference_only_files()
    assert len(flagged) == 4
    for file_name in flagged:
        # locate the manifest entry, then fetch it via its title
        entry = next(e for e in brain_loader.templates() if e["file"] == file_name)
        hits = retrieval.retrieve(entry["title"], limit=152)
        match = next((hit for hit in hits if hit.file == file_name), None)
        assert match is not None, f"{file_name} not retrievable for its own title"
        assert match.reference_only is True


def test_retrieval_excludes_reference_only_when_asked():
    title = "Pangastritis"
    included = {hit.file for hit in retrieval.retrieve(title, limit=152, include_reference_only=True)}
    excluded = {hit.file for hit in retrieval.retrieve(title, limit=152, include_reference_only=False)}
    assert "Pangastritis.md" in included
    assert "Pangastritis.md" not in excluded


# --------------------------------------------------------------------------- prompt


def test_prompt_contains_kern_rules_playbook_and_mandate():
    bundle = build_prompt(
        doc_type="arztbrief",
        dictation="Rohtext mit {{LAST_NAME}}.",
        letterhead={"practice_name": "Praxis Dr. Weber"},
        patient_ctx={"last_name": "{{LAST_NAME}}"},
        custom_rules="Immer die Kurzform verwenden.",
    )
    assert bundle.regelwerk_rules == 67
    assert "R1:" in bundle.system and "R67:" in bundle.system
    assert "AP-01:" in bundle.system and "AP-25:" in bundle.system
    assert "K1.3" in bundle.system  # kern core rule
    assert "PLAYBOOK DOKUMENTTYP" in bundle.system
    assert "Diagnosen:" in bundle.system and "ambulante Therapieempfehlungen" in bundle.system
    assert "reiner Plain-Text" in bundle.system or "Plain-Text" in bundle.system
    assert "PRAXISREGELN DES MITGLIEDS" in bundle.user and "Kurzform" in bundle.user
    assert "{{LAST_NAME}}" in bundle.user  # pseudonym contract preserved
    assert "Müller" not in bundle.system and "Müller" not in bundle.user


def test_prompt_excludes_licensed_prose_and_flags_reference_only():
    hits = retrieval.retrieve("Pangastritis", limit=3)
    bundle = build_prompt(
        doc_type="arztbrief",
        dictation="Rohtext.",
        letterhead={},
        patient_ctx={},
        templates=hits,
    )
    ref = [hit for hit in hits if hit.reference_only]
    assert ref
    assert "REFERENCE-ONLY" in bundle.user
    assert ref[0].file in bundle.reference_only_files


def test_prompt_never_carries_raw_patient_identifiers():
    from briefato.pipeline.pseudonym import Pseudonymizer
    from datetime import date

    class _P:
        first_name = "Qwerta"
        last_name = "Zzyzx"
        birth_date = date(1968, 11, 23)
        insurance_number = "X999888777"
        street = "Fantasieweg 5"
        zip = "10115"
        city = "Berlin"
        phone = "030 998877"
        email = "qwert.zzyzx@example.de"
        sex = "w"

    pz = Pseudonymizer.from_patient(_P())
    raw_dictation = (
        "Patientin Qwerta Zzyzx, geb. 23.11.1968, Fantasieweg 5, Tel. 030 998877, "
        "E-Mail qwert.zzyzx@example.de."
    )
    bundle = build_prompt(
        doc_type="arztbrief",
        dictation=pz.mask(raw_dictation),
        letterhead={"practice_name": "Praxis Dr. Weber"},
        patient_ctx={key: pz.mask(value) for key, value in pz.masked_fields().items()},
    )
    captured = f"{bundle.system}\n{bundle.user}"
    for raw in ("Zzyzx", "Qwerta", "23.11.1968", "1968-11-23", "X999888777", "Fantasieweg 5", "998877"):
        assert raw.lower() not in captured.lower(), f"raw identifier leaked: {raw}"
    assert "{{LAST_NAME}}" in captured


def test_prompt_version_is_stamped():
    bundle = build_prompt(doc_type="zusammenfassung", dictation="x", letterhead={}, patient_ctx={})
    assert bundle.prompt_version == prompt_assembly.PROMPT_VERSION
    assert prompt_assembly.PROMPT_VERSION in bundle.system


# --------------------------------------------------------------------------- rule checker

BAD_TEXT = """Hiermit berichten wir über die o. g. Patientin.

**Anamnese:** seit drei Tagen Oberbauchschmerzen. Sonographie: Cholelithiasis. Labor: CRP 87.

KU: Druckschmerz im rechten Oberbauch; Abwehrspannung; LLS positiv.

Die Histologie steht noch aus; die Patientin erhielt Ueberweisung.

Diagnosen:
Z.n. Cholezystektomie
Cholezystolithiasis (ICD-10 K80.2)

Zusammenfassend lässt sich sagen: guter Verlauf. Ueberweisung an die Chirurgie."""

GOOD_TEXT = """Die Patientin stellte sich mit dem Rettungsdienst bei seit vier Wochen bestehender atraumatischer Ulzeration am rechten Unterschenkel vor. Wir nahmen die Patientin zur weiteren Diagnostik bzw. Schmerztherapie stationär auf.
In der KU zeigte sich eine 3 × 3 cm große Ulzeration mit fibrinbelegtem Wundgrund, die peripheren Pulse waren tastbar.
Zur Abklärung erfolgte eine Duplexsonographie, wobei sich eine chronisch venöse Insuffizienz zeigte.
Im Verlauf gestaltete sich die Wundheilung regelrecht, der Kostaufbau wurde vertragen.
Nach klinischer Besserung entließen wir die Patientin am 07.05.2026 in die häusliche Pflege.

ambulante Therapieempfehlungen nach der Entlassung:
Wir empfahlen die regelmäßige Wundkontrolle und ausreichende Mobilisation. Vielen Dank für die Weiterbetreuung.

Diagnosen:
Ulcus cruris venosum
Chronisch venöse Insuffizienz

Nebenerkrankungen:
keine

Therapie-Maßnahmen auf der Station:
OP am 17.04.2026: Wunddébridement
Kompressionstherapie"""


def test_rule_checker_passes_a_compliant_draft():
    result = check(GOOD_TEXT, "arztbrief", "Ulcus cruris venosum")
    assert result.ok is True
    assert result.hard == []
    assert result.summary == "keine Regelverstöße"


def test_rule_checker_flags_every_anti_pattern_on_a_bad_draft():
    result = check(BAD_TEXT, "arztbrief", "Patientin mit Oberbauchschmerzen und Gallensteinen.")
    assert result.ok is False
    rules = {finding.rule_id for finding in result.findings}
    # markdown, category labels, intro, closing, Dg.-free list, dates, semicolon,
    # umlauts, invented ICD, content after Diagnosen, Z.n. line
    assert {"R2", "R3", "R4", "R5", "R6", "R8", "R21", "R23", "R46"} <= rules
    assert all(finding.rule_id for finding in result.findings)
    assert result.correction_instructions()
    assert any(finding.severity == "hard" for finding in result.findings)


def test_rule_checker_detects_wrong_document_type_blocks():
    # a Therapie-Maßnahmen block must not appear in an ambulant letter (R30)
    text = "Der Patient stellte sich ambulant vor. Diagnosen:\nLeistenhernie\n\nTherapie-Maßnahmen auf der Station:\nOP am 01.09.2026: TAPP"
    result = check(text, "ambulant", "Leistenhernie ambulant operiert")
    assert "R30" in {finding.rule_id for finding in result.findings}


def test_rule_checker_flags_missing_diagnosen_for_zusammenfassung_conflict():
    text = "Der Patient wurde im Sep. 2026 operativ versorgt. Diagnosen:\nCholezystolithiasis"
    result = check(text, "zusammenfassung", "OP-Diktat")
    assert "R24" in {finding.rule_id for finding in result.findings}


def test_rule_checker_summary_and_serialisation():
    result = check(BAD_TEXT, "arztbrief", "")
    payload = result.as_dict()
    assert payload["ok"] is False
    assert payload["hard"] and isinstance(payload["hard"][0], dict)
    assert "harte" in result.summary


@pytest.mark.parametrize(
    "text,doc_type,expected_rule",
    [
        # 'Dg.:' prefix
        ("Befund. Dg.: Cholezystitis", "arztbrief", "R22"),
        # narrative date in the course
        ("Am 12.03.2026 zeigte sich eine Besserung der Beschwerden.", "arztbrief", "R10"),
        # KI/disclaimer text
        ("Dieser Brief wurde KI-generiert und ersetzt keine ärztliche Beratung.", "arztbrief", "AP-06"),
        # repeated finding
        (
            "Die Patientin klagte über zunehmende Schmerzen im rechten Unterbauch und Fieber. "
            "Die Patientin klagte über zunehmende Schmerzen im rechten Unterbauch und Fieber.",
            "arztbrief",
            "R13",
        ),
        # wrong block order (Diagnosen before the ambulante Empfehlungen)
        (
            "Diagnosen:\nCholezystitis\n\nambulante Therapieempfehlungen nach der Entlassung:\nKontrolle\n\n"
            "Nebenerkrankungen:\nkeine\n\nTherapie-Maßnahmen auf der Station:\nCHE",
            "arztbrief",
            "R25",
        ),
    ],
)
def test_rule_checker_flags_specific_anti_patterns(text, doc_type, expected_rule):
    result = check(text, doc_type, "Rohtext ohne ICD")
    assert expected_rule in {finding.rule_id for finding in result.findings}

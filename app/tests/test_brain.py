"""Brain tests (WORKSTREAM-BRAIN-WIRING) — loader, triage, retrieval, prompt, checker.

Offline only. Run with::

    cd /workspace/briefato && .venv/bin/python -m pytest app/tests/test_brain.py -q
"""

from __future__ import annotations

import re

import pytest

from briefato.brain import brain_loader, muster_merge, prompt_assembly, retrieval, rule_checker, triage
from briefato.brain.prompt_assembly import build_prompt
from briefato.brain.rule_checker import autofix_umlauts, check
from briefato.brain.stopwords import is_qualifier
from briefato.brain.triage import DOC_TYPES, TriageDecision


# --------------------------------------------------------------------------- loader


def test_loader_finds_the_brain():
    status = brain_loader.status()
    assert brain_loader.kern_text().strip()
    assert len(brain_loader.rules()) == 67
    assert len(brain_loader.anti_pattern_lines()) == 25
    assert status["templates"] == 144  # 152 source templates minus 11 absorbed in 7 merge groups
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


# --------------------------------------------------------------------------- retrieval precision (WORKSTREAM-BRAIN-V2)


def test_retrieval_selftest_queries_rank_first():
    """All 15 self-test queries return the correct template at rank 1."""
    for query, expected in retrieval.SELFTEST_QUERIES:
        hits = retrieval.retrieve(query, limit=1)
        assert hits, f"no retrieval hit for {query!r}"
        top = hits[0]
        if expected == "Cholezystolithiasis.md":
            # scrub-pending and therefore intentionally excluded; the biliary family wins
            assert re.search(r"gallen|chole", top.file, re.IGNORECASE), top.file
        else:
            assert expected.lower() in top.file.lower(), f"{query!r} -> {top.file}"
        assert top.reason, f"every hit must carry a German reason ({query!r})"


def _reason_token(hit):
    token = hit.reason.split(":", 1)[-1].strip() if ":" in hit.reason else ""
    return token.split()[0].lower() if token else ""


@pytest.mark.parametrize("query,expected", retrieval.ADVERSARIAL_QUERIES)
def test_retrieval_adversarial_generic_adjective_never_wins(query, expected):
    """The correct template must beat any template that only shares a generic adjective."""
    hits = retrieval.retrieve(query, limit=25)
    assert hits, f"no retrieval hit for {query!r}"
    top = hits[0]
    assert expected.lower() in top.file.lower(), f"{query!r} -> {top.file}"
    # the winning match is never a generic clinical qualifier
    assert not is_qualifier(_reason_token(top)), top.reason
    # and no template whose only match is a qualifier may outrank the top hit
    for hit in hits[1:]:
        if _reason_token(hit) and is_qualifier(_reason_token(hit)):
            assert hit.score < top.score, f"{hit.file} outranked the correct template"


def test_diverticulitis_dictation_beats_subdural_template():
    """The exact staging defect: diverticulitis must beat the subdural template."""
    query = retrieval.ADVERSARIAL_QUERIES[0][0]
    ranked = {hit.file: hit.score for hit in retrieval.retrieve(query, limit=50)}
    assert "Akute_Divertikulitis.md" in ranked
    # The subdural template must not be retrieved at all, or score strictly lower.
    subdural_score = ranked.get("Akut_auf_chronisches_Subduralhaematom.md", 0.0)
    assert ranked["Akute_Divertikulitis.md"] > subdural_score


def test_generic_qualifiers_are_not_strong_keyword_matches():
    # 'akut'/'chronisch' are down-weighted: a query made of adjectives only is weak.
    hits = retrieval.retrieve("akute chronische Verschlechterung", limit=1)
    if hits:
        assert hits[0].score < retrieval.W_KEYWORD


# --------------------------------------------------------------------------- near-duplicate merges (product copy only)


def test_manifest_has_one_entry_per_merged_group_with_merged_from():
    merged = {entry["file"]: entry for entry in brain_loader.templates() if entry.get("merged_from")}
    groups = {group.file: group for group in muster_merge.groups()}
    assert set(merged) == set(groups)
    for file_name, entry in merged.items():
        assert entry["merged_from"] == groups[file_name].absorbed
        assert entry["indication_keywords"], "absorbed synonyms must be folded in"
        assert entry["licence_risk"] in {"low", "review"}


def test_absorbed_templates_are_gone_from_the_manifest():
    files = {entry["file"] for entry in brain_loader.templates()}
    for absorbed in muster_merge.absorbed_files():
        assert absorbed not in files, f"absorbed template still in manifest: {absorbed}"


def test_merged_synonyms_still_retrieve_the_kept_template():
    cases = [
        ("Erysipel Wundrose", "Erysipel.md"),
        ("pAVK Mediasklerose", "pAVK.md"),
        ("Papilläre Pankreatitis", "Biliaere_Pankreatitis.md"),
        ("Diabetes mellitus Typ 1", "Diabetes_mellitus.md"),
        ("Kontusion Kleinzehe", "Kontusion_Zehen.md"),
        ("Narbenhernie IPOM", "Narbenhernien_epigastrisch.md"),
    ]
    for query, expected_file in cases:
        hits = retrieval.retrieve(query, limit=5)
        assert any(hit.file == expected_file for hit in hits), f"{query!r} -> {[h.file for h in hits]}"


def test_merged_packaged_files_are_deterministic():
    """The packaged merged templates equal what the packer would generate (--check semantics)."""
    from pathlib import Path

    source = Path(str(brain_loader.manifest().get("source")))
    dest = brain_loader.brain_root() / "musterbriefe" / "templates"
    for group in muster_merge.groups():
        if not source.is_dir():  # pragma: no cover - archive not mounted
            pytest.skip("source archive not available")
        expected = muster_merge.build_merged_content(source, group)
        assert (dest / group.file).read_text(encoding="utf-8") == expected


def test_merge_map_documents_every_group_and_non_merge():
    payload = muster_merge.load_merge_map()
    for group in payload.get("groups", []):
        assert group.get("reason"), group.get("id")
        assert len(group.get("sources", [])) >= 2
    assert payload.get("non_merges"), "deliberate non-merges must be documented"
    for non_merge in payload["non_merges"]:
        assert non_merge.get("reason")


# --------------------------------------------------------------------------- triage: 'nachweis' fix
#
# Real-model harness finding: a bare `nachweis` (e.g. "Malignitätsnachweis") mis-routed a
# clinical dictation to weiterbildung-kv-nachweise. It must only do so in a real
# KV/WBO/Weiterbildung/Logbuch/QZ/QS context.


@pytest.mark.parametrize(
    "dictation,expected",
    [
        # a clinical finding word must stay clinical
        ("Stationärer Entlassbrief mit Malignitätsnachweis in der Histologie.", ("arztbrief",)),
        ("Sputum: Nachweis von Streptococcus pneumoniae.", ("arztbrief",)),
        # ... whereas a real Nachweis request keeps routing there
        ("Bitte den KV-Nachweis für die Weiterbildung erstellen.", ("weiterbildung-kv-nachweise",)),
        ("WBO / KV-Genehmigung als Nachweis.", ("weiterbildung-kv-nachweise",)),
        ("Nachweis der QZ-Teilnahme bitte.", ("weiterbildung-kv-nachweise",)),
    ],
)
def test_triage_nachweis_requires_a_weiterbildung_context(dictation, expected):
    decision = triage.triage(dictation)
    assert decision.doc_types == expected, decision.reason


# --------------------------------------------------------------------------- R5: broadened labels


@pytest.mark.parametrize(
    "text,doc_type",
    [
        # the judge's quoted label-like list opener (no colon)
        ("Abschließende Kontrolle auf intraabdominelle Bluttrockenheit, welche besteht.", "operationsbericht"),
        # a colon label that was previously not in the list
        ("Mikrobiologie: Nachweis von Streptococcus pneumoniae.", "arztbrief"),
        ("Diagnostik: Sonographie des Abdomens.", "arztbrief"),
    ],
)
def test_rule_checker_flags_broadened_category_labels(text, doc_type):
    result = check(text, doc_type, "")
    assert "R5" in {finding.rule_id for finding in result.findings}


# --------------------------------------------------------------------------- R6 autofix


def test_autofix_normalises_curated_transliterations():
    fixed, replacements = autofix_umlauts(
        "Die stationaer aufgenommene Patientin hat Fluessigkeit und grosse Beschwerden."
    )
    assert "stationär" in fixed
    assert "Flüssigkeit" in fixed
    assert "große" in fixed
    assert "stationaer" not in fixed and "Fluessigkeit" not in fixed
    assert ("stationaer", "stationär") in replacements
    assert ("Fluessigkeit", "Flüssigkeit") in replacements


def test_autofix_never_touches_words_where_ae_oe_ue_ss_is_correct():
    original = (
        "Das Aerosol, der Oesophagus und das Museum sind keine Umlautfehler; "
        "auch Prozess und Fluss bleiben unverändert."
    )
    fixed, replacements = autofix_umlauts(original)
    assert fixed == original
    assert replacements == []


def test_check_logs_umlaut_autofix_as_a_soft_finding():
    cleaned, replacements = autofix_umlauts("stationaer aufgenommen")
    result = check(cleaned, "arztbrief", "irgendein Rohtext", autofix=replacements)
    autofix_findings = [finding for finding in result.findings if finding.rule_id == "R6-AUTOFIX"]
    assert autofix_findings
    assert all(finding.severity == "soft" for finding in autofix_findings)
    assert "stationär" in autofix_findings[0].message


# --------------------------------------------------------------------------- R-INVENT (anti-invention)

_AMBULANT02_DICTATION = (
    "Das Kind stellte sich in Begleitung seiner Mutter in der NFA vor, nachdem es sich beim Spielen "
    "den Kopf gestossen hatte. In der KU zeigte sich an der Stirn oberhalb der linken Augenbraue eine "
    "ca. 0,5 cm grosse Kopfplatzwunde; neurologisch war das Kind unauffaellig.\n\n"
    "Die Wunde wurde desinfiziert, mit Fibrinkleber adaptiert und mit Pflaster verbunden. Die Mutter "
    "wurde über das weitere Vorgehen aufgeklaert; der Hautkleber löst sich nach etwa 3 Tagen von selbst. "
    "Eine stationaere Aufnahme war nicht erforderlich.\n\n"
    "Diagnosen:\nPlatzwunde der Stirn\nCommotio cerebri ausgeschlossen"
)

_OPBERICHT01_DICTATION = (
    "OP-Bericht. Bei der 54-jaehrigen Patientin besteht eine symptomatische Cholezystolithiasis ohne "
    "Anhalt fuer eine Gallenwegsobstruktion. Bei symptomatischem Steinleiden erfolgte die geplante "
    "laparoskopische Cholezystektomie. OP: OP am 23.09.2026: laparoskopische Cholezystektomie. "
    "Intraoperativ zeigte sich eine chronisch entzuendete Gallenblase mit multiplen Konkrementen. "
    "Präparat: Gallenblase, Präparat ad Histologie. Diagnosen: Symptomatische Cholezystolithiasis "
    "Operation: Laparoskopische Cholezystektomie"
)


def test_rule_checker_catches_the_invented_recommendation_sentence():
    """The judge scored this exact sentence 1/5 (ambulant-02) — it must be an R-INVENT."""
    text = (
        "Das Kind stellte sich in Begleitung seiner Mutter in der NFA vor.\n\n"
        "Empfohlen werden die regelmäßige Wundkontrolle sowie die Wiedervorstellung bei Rötung, "
        "Schwellung, zunehmenden Schmerzen oder Fieber.\n\n"
        "Diagnosen:\nPlatzwunde der Stirn"
    )
    result = check(text, "ambulant", _AMBULANT02_DICTATION)
    invented = [finding for finding in result.hard if finding.rule_id == "R-INVENT"]
    assert invented, [finding.rule_id for finding in result.hard]
    message = invented[0].message.lower()
    assert "wundkontrolle" in message and "wiedervorstellung" in message
    # the offending passage is quoted for the UI
    assert "Wundkontrolle" in invented[0].evidence


def test_rule_checker_catches_the_invented_op_standard_text():
    """The judge scored this OP sentence 0/5 (opbericht-01)."""
    text = (
        "Bei der 54-jährigen Patientin besteht eine symptomatische Cholezystolithiasis.\n\n"
        "Nach Team-Time-out erfolgt die Hautdesinfektion gefärbt sowie die sterile Abdeckung des Abdomens.\n\n"
        "Diagnosen:\nSymptomatische Cholezystolithiasis\n\nOperation:\nLaparoskopische Cholezystektomie"
    )
    result = check(text, "operationsbericht", _OPBERICHT01_DICTATION)
    invented = [finding for finding in result.hard if finding.rule_id == "R-INVENT"]
    assert invented, [finding.rule_id for finding in result.hard]
    assert "hautdesinfektion" in invented[0].message.lower()


def test_rule_checker_tolerates_faithful_rephrasing_via_synonyms():
    source = (
        "Die Patientin wurde mit Unterbauchbeschwerden stationär aufgenommen. Sonographisch zeigte sich "
        "eine entzündlich verdickte Sigma-Schlinge. Laborchemisch bestanden eine Leukozytose und ein "
        "erhöhtes CRP. Wir nahmen die Patientin zur intravenösen Antibiotikatherapie stationär auf."
    )
    faithful = (
        "Die Aufnahme der Patientin erfolgte bei Unterbauchschmerzen. Sonographisch zeigte sich eine "
        "entzündlich verdickte Sigma-Schlinge. Eine Leukozytose und ein erhöhtes CRP bestanden."
    )
    assert "R-INVENT" not in {finding.rule_id for finding in check(faithful, "arztbrief", source).findings}
    # the same source with a genuinely novel sentence DOES fire — proves the check is active here
    invented = faithful + " Empfohlen wird eine Wiedervorstellung bei Rötung, Schwellung oder Fieber."
    assert "R-INVENT" in {finding.rule_id for finding in check(invented, "arztbrief", source).findings}


def test_invention_check_is_deterministic_and_fast_on_two_pages():
    import time

    paragraph = (
        "Die Patientin klagte über seit zwei Tagen bestehende rechtsseitige Oberbauchschmerzen mit "
        "Ausstrahlung. Sonographisch zeigte sich eine entzündlich verdickte Gallenblasenwand mit Konkrementen. "
        "Laborchemisch bestanden eine Leukozytose und ein erhöhtes CRP."
    )
    text = "\n".join(paragraph for _ in range(14))  # ~2 pages
    calls = [check(text, "arztbrief", _AMBULANT02_DICTATION) for _ in range(2)]
    first = [finding.as_dict() for finding in calls[0].findings]
    second = [finding.as_dict() for finding in calls[1].findings]
    assert first == second  # deterministic

    start = time.perf_counter()
    check(text, "arztbrief", _AMBULANT02_DICTATION)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.1, f"R-INVENT too slow: {elapsed * 1000:.1f} ms on {len(text)} chars"

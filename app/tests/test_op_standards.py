"""Department OP standards — harvest, selection, prompt skeleton, grounding.

OWNER: WORKSTREAM-OP-STANDARDS.

The measured failure (real model, 2026-10-02): the OP-Bericht cases lost their routine
steps (``Team-Time-out`` / ``Capnoperitoneum`` / ``Desinfektion`` / ``Wundverschluss``
missing) because the reference material itself did not carry the department standards.
Fix under test: ``brain/standards/*.md`` are injected into every OP-Bericht prompt as a
labelled ``ABTEILUNGSSTANDARD`` skeleton (enrichment-toggle independent) and are part of
the reference text handed to the rule checker (soft ``R-REFERENZ``, never hard
``R-INVENT``).

Offline only. Run with::

    cd /workspace/briefato && .venv/bin/python -m pytest app/tests/test_op_standards.py -q
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

TMP = tempfile.mkdtemp(prefix="briefato-opstd-")
os.environ.setdefault("BRIEFATO_DATA_DIR", TMP)
os.environ.setdefault("BRIEFATO_DB_URL", f"sqlite:///{Path(TMP) / 'opstd.db'}")
os.environ.setdefault("BRIEFATO_LLM_MOCK", "true")
os.environ.setdefault("BRIEFATO_SECRET_KEY", "opstd-secret")

import pytest  # noqa: E402

from briefato.brain import brain_loader, standards  # noqa: E402
from briefato.brain.prompt_assembly import (  # noqa: E402
    build_prompt,
    build_weave_prompt,
    reference_support_text,
)
from briefato.brain.rule_checker import check as rule_check  # noqa: E402

CHE_DICTATION = (
    "OP-Bericht.\n\n"
    "Bei der 54-jaehrigen Patientin besteht eine symptomatische Cholezystolithiasis ohne Anhalt "
    "fuer eine Gallenwegsobstruktion. Bei symptomatischem Steinleiden erfolgte die geplante "
    "laparoskopische Cholezystektomie.\n\n"
    "OP:\nOP am 23.09.2026: laparoskopische Cholezystektomie. Intraoperativ zeigte sich eine "
    "chronisch entzuendete Gallenblase mit multiplen Konkrementen.\n\n"
    "Präparat:\nGallenblase, Präparat ad Histologie.\n\n"
    "Diagnosen:\nSymptomatische Cholezystolithiasis\n\n"
    "Operation:\nLaparoskopische Cholezystektomie"
)

NARBEN_DICTATION = (
    "OP-Bericht.\n\n"
    "Bei dem 68-jaehrigen Patienten besteht eine Narbenhernie nach Medianlaparotomie mit "
    "zunehmender Grösse und Beschwerden. Die operative Versorgung erfolgte mittels Sublay-Technik "
    "und Netzimplantation 15 x 20 cm.\n\n"
    "OP:\nOP am 29.09.2026: Narbenhernienversorgung in Sublay-Technik. Intraoperativ zeigte sich "
    "eine ca. 6 cm grosse Narbenhernie ohne Inkarzeration.\n\n"
    "Diagnosen:\nNarbenhernie nach Medianlaparotomie\n\n"
    "Operation:\nNarbenhernienversorgung in Sublay-Technik"
)

GENERIC_DICTATION = (
    "OP-Bericht.\n\nBei dem Patienten erfolgte am 01.10.2026 die laparoskopische Appendektomie bei "
    "akuter Appendizitis. Der postoperative Verlauf war unauffällig.\n\n"
    "Diagnosen:\nAkute Appendizitis\n\nOperation:\nLaparoskopische Appendektomie"
)

STANDARDS_FILES = (
    "index.md",
    "op-standardschritte.md",
    "che-laparoskopisch.md",
    "narbenhernie-sublay.md",
)


# --------------------------------------------------------------------------- harvest


def test_standards_are_harvested_and_provenance_tagged():
    for name in STANDARDS_FILES:
        text = brain_loader.standard_text(name)
        assert text.strip(), name
    for name in ("op-standardschritte.md", "che-laparoskopisch.md", "narbenhernie-sublay.md"):
        assert "provenance:" in brain_loader.standard_text(name), name


def test_generic_catalogue_lists_the_not_allowed_steps():
    text = brain_loader.standard_text("op-standardschritte.md")
    # the "may not be added without evidence" list (method rule)
    assert "Nicht ohne Beleg ergänzen" in text
    assert "Blutsperre" in text and "Drainage" in text
    assert "Situsdetails" in text
    # the department standards carry their internal trigger word
    assert "Capnoperitoneum" in brain_loader.standard_text("che-laparoskopisch.md")
    assert "Sublay" in brain_loader.standard_text("narbenhernie-sublay.md")
    # the index documents the trigger keywords
    index = brain_loader.standards_index_text()
    assert "cholezystektomie" in index and "narbenhernie" in index and "sublay" in index


# --------------------------------------------------------------------------- selection


def test_index_selects_by_trigger_keywords():
    assert standards.select("operationsbericht", CHE_DICTATION).file == "che-laparoskopisch.md"
    assert standards.select("operationsbericht", NARBEN_DICTATION).file == "narbenhernie-sublay.md"
    assert standards.select("operationsbericht", GENERIC_DICTATION).file == "op-standardschritte.md"
    # title-only selection works too (the demo passes the dictation, a caller may pass a title)
    assert standards.select("operationsbericht", "laparoskopische Cholezystektomie").file == "che-laparoskopisch.md"


def test_short_trigger_che_does_not_match_inside_a_word():
    # "che" must match as a whole word only — never inside "Chemotherapie".
    entry = standards.select("operationsbericht", "Port-Implantation bei Chemotherapie")
    assert entry is not None and entry.file == "op-standardschritte.md"


def test_only_the_operationsbericht_receives_a_standard():
    for doc_type in brain_loader.DOKUMENTTYPEN:
        if doc_type == "operationsbericht":
            assert standards.select(doc_type, CHE_DICTATION) is not None
        else:
            assert standards.select(doc_type, CHE_DICTATION) is None, doc_type


# --------------------------------------------------------------------------- prompt


def test_op_prompt_contains_the_abteilungsstandard_block_with_enrichment_off():
    bundle = build_prompt(doc_type="operationsbericht", dictation=CHE_DICTATION)
    assert standards.STANDARD_HEADER in bundle.user
    assert standards.standard_block("operationsbericht", CHE_DICTATION) in bundle.user
    assert bundle.standard_files == ["che-laparoskopisch.md"]
    # the four routine terms the eval case requires are handed to the model
    for term in ("Team-Time-out", "Hautdesinfektion", "Capnoperitoneum", "Wundverschluss"):
        assert term in bundle.user, term


def test_narbenhernie_dictation_selects_the_sublay_standard():
    bundle = build_prompt(doc_type="operationsbericht", dictation=NARBEN_DICTATION)
    assert bundle.standard_files == ["narbenhernie-sublay.md"]
    assert standards.STANDARD_HEADER in bundle.user
    for term in ("Team-Time-out", "Hautdesinfektion", "Netz", "Wundverschluss"):
        assert term in bundle.user, term


def test_generic_op_dictation_falls_back_to_the_catalogue():
    bundle = build_prompt(doc_type="operationsbericht", dictation=GENERIC_DICTATION)
    assert bundle.standard_files == ["op-standardschritte.md"]
    assert standards.STANDARD_HEADER in bundle.user


@pytest.mark.parametrize(
    "doc_type",
    sorted(dt for dt in brain_loader.DOKUMENTTYPEN if dt != "operationsbericht"),
)
def test_non_op_document_types_never_get_the_block(doc_type):
    bundle = build_prompt(doc_type=doc_type, dictation=CHE_DICTATION)
    assert standards.STANDARD_HEADER not in bundle.user
    assert standards.STANDARD_HEADER not in bundle.system
    assert bundle.standard_files == []


def test_weave_prompt_also_carries_the_standard_for_op_only():
    compressed = [{"type": "op_bericht", "text": "OP am 23.09.2026: laparoskopische Cholezystektomie."}]
    op = build_weave_prompt(doc_type="operationsbericht", compressed=compressed, dictation=CHE_DICTATION)
    assert standards.STANDARD_HEADER in op.user
    assert op.standard_files == ["che-laparoskopisch.md"]
    other = build_weave_prompt(doc_type="arztbrief", compressed=compressed, dictation=CHE_DICTATION)
    assert standards.STANDARD_HEADER not in other.user
    assert other.standard_files == []


# --------------------------------------------------------------------------- grounding


def test_reference_support_text_includes_the_standard_for_op_only():
    op = reference_support_text([], None, doc_type="operationsbericht", dictation=CHE_DICTATION)
    assert "Capnoperitoneum" in op and "Team-Time-out" in op
    other = reference_support_text([], None, doc_type="arztbrief", dictation=CHE_DICTATION)
    assert "Capnoperitoneum" not in other


def test_standard_step_paragraph_is_soft_referenz_and_never_invent():
    routine = "Nach Team-Time-out erfolgte die Hautdesinfektion sowie die sterile Abdeckung des Abdomens."
    text = (
        f"{CHE_DICTATION}\n\n{routine}\n\n"
        "Diagnosen:\nSymptomatische Cholezystolithiasis\n\n"
        "Operation:\nLaparoskopische Cholezystektomie"
    )
    # without the standard as reference the routine step counts as invention (check is active)
    without = rule_check(text, "operationsbericht", CHE_DICTATION)
    assert "R-INVENT" in {finding.rule_id for finding in without.hard}

    reference = standards.standard_reference("operationsbericht", CHE_DICTATION)
    with_ref = rule_check(text, "operationsbericht", CHE_DICTATION, reference=reference)
    assert "R-INVENT" not in {finding.rule_id for finding in with_ref.hard}
    assert "R-REFERENZ" in {finding.rule_id for finding in with_ref.soft}
    assert all(
        finding.severity == "soft" for finding in with_ref.findings if finding.rule_id == "R-REFERENZ"
    )


def test_injected_block_terms_survive_into_the_checker_reference():
    bundle = build_prompt(doc_type="operationsbericht", dictation=CHE_DICTATION)
    reference = reference_support_text([], None, doc_type="operationsbericht", dictation=CHE_DICTATION)
    for term in ("Team-Time-out", "Hautdesinfektion", "Capnoperitoneum", "Wundverschluss"):
        assert term in bundle.user and term in reference, term

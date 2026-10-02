"""Parent-side regression: reference knowledge must not be reported as invention.

Found during integration review 2026-10-02: the anti-invention check (R-INVENT) only compared the
output against the *dictation*. With grounded enrichment / retrieved Musterbrief sections enabled, a
letter that correctly uses archive-derived standard technique (e.g. "Nach Team-Time-out erfolgt die
Hautdesinfektion gefärbt sowie die sterile Abdeckung des Abdomens.") was reported as invented and
triggered a corrective retry — the opposite of the method's rule that standard details may be derived
from the archive.

Fix under test: `rule_checker.check(..., reference=...)` treats reference-backed terms as supported
and reports them as the soft note `R-REFERENZ` instead.

Second finding (same review): with a short dictation the whole check was skipped
(`_RINVENT_MIN_SOURCE_TERMS`), including the one case the LLM judge flagged in production — an
invented follow-up recommendation in a 450-char ambulant letter. Thin inputs now keep the
recommendation check active and skip everything else.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

TMP = tempfile.mkdtemp(prefix="briefato-refground-")
os.environ.setdefault("BRIEFATO_DATA_DIR", TMP)
os.environ.setdefault("BRIEFATO_DB_URL", f"sqlite:///{Path(TMP) / 'ref.db'}")
os.environ.setdefault("BRIEFATO_LLM_MOCK", "true")
os.environ.setdefault("BRIEFATO_SECRET_KEY", "ref-secret")

from briefato.brain import rule_checker  # noqa: E402
from briefato.brain import prompt_assembly  # noqa: E402
from briefato.brain import standards  # noqa: E402
from briefato.brain.prompt_assembly import reference_support_text  # noqa: E402

# Rich dictation (>12 substantive source terms) — the ordinary path.
DICTATION = (
    "Patient mit akuter Appendizitis, seit dem Vortag bestehende Schmerzen im rechten Unterbauch, "
    "kein Fieber, keine Übelkeit. Wir nahmen den Pat. zur weiteren Diagnostik stationaer auf. "
    "Sonographie: vergroesserte Appendix ohne freie Fluessigkeit. Labor: Leukozyten erhoeht, "
    "CRP erhoeht. Op am 17.04.2026: laparoskopische Appendektomie, Appendix geborgen, keine "
    "Drainage. Verlauf unauffaellig, Kostaufbau problemlos, Entlassung am 20.04.2026."
)
OUTPUT = (
    "Wir nahmen den Pat. zur weiteren Diagnostik stationär auf. Sonographisch zeigte sich eine "
    "vergrößerte Appendix ohne freie Flüssigkeit. Nach Team-Time-out erfolgt die Hautdesinfektion "
    "gefärbt sowie die sterile Abdeckung des Abdomens. Am 20.04.2026 entließen wir den Pat. "
    "beschwerdefrei.\n\nDiagnosen:\nAkute Appendizitis"
)
REFERENCE = (
    "Musterbrief Appendizitis — Therapie: Nach Team-Time-out erfolgt die Hautdesinfektion gefärbt "
    "sowie die sterile Abdeckung des Abdomens. Anschließend laparoskopische Appendektomie mit "
    "Bergung über den Nabel."
)

# Thin dictation (ambulant letter) — the path that used to skip the check entirely.
THIN_DICTATION = (
    "Das Kind stellte sich nach Kopfstoss beim Spielen vor. Kopfplatzwunde an der Stirn, "
    "neurologisch unauffaellig. Wunddesinfektion, Adaptation mit Fibrinkleber, Pflasterverband. "
    "Keine stationaere Aufnahme noetig."
)
THIN_OUTPUT = (
    "Das Kind stellte sich nach Kopfstoß beim Spielen vor. An der Stirn zeigte sich eine "
    "Kopfplatzwunde, der neurologische Befund war unauffällig. Wir führten eine Wunddesinfektion "
    "durch und adaptierten die Wunde mit Fibrinkleber. Empfohlen werden die regelmäßige "
    "Wundkontrolle sowie die Wiedervorstellung bei Rötung, Schwellung, zunehmenden Schmerzen "
    "oder Fieber."
)


def _hard_ids(result) -> set[str]:
    return {finding.rule_id for finding in result.hard}


def test_standard_sentence_is_invention_without_reference():
    result = rule_checker.check(OUTPUT, "operationsbericht", DICTATION)
    assert "R-INVENT" in _hard_ids(result), [f.rule_id for f in result.hard]


def test_same_sentence_is_only_a_reference_note_with_reference():
    result = rule_checker.check(OUTPUT, "operationsbericht", DICTATION, reference=REFERENCE)
    assert "R-INVENT" not in _hard_ids(result), [f.rule_id for f in result.hard]
    soft_ids = {finding.rule_id for finding in result.soft}
    assert "R-REFERENZ" in soft_ids, soft_ids


def test_invented_recommendation_in_thin_dictation_is_caught():
    """The exact defect the LLM judge scored 1/5 on ambulant-02."""
    result = rule_checker.check(THIN_OUTPUT, "ambulant", THIN_DICTATION)
    assert "R-INVENT" in _hard_ids(result), [f.rule_id for f in result.hard]
    evidence = " ".join(f.evidence for f in result.hard if f.rule_id == "R-INVENT")
    assert "Wundkontrolle" in evidence or "Wiedervorstellung" in evidence


def test_thin_dictation_without_recommendation_stays_silent():
    faithful = "Das Kind stellte sich nach Kopfstoß beim Spielen vor. Die Wunde wurde versorgt."
    result = rule_checker.check(faithful, "ambulant", THIN_DICTATION)
    assert "R-INVENT" not in _hard_ids(result), [f.rule_id for f in result.hard]


def test_reference_support_text_collects_enrichment_and_template_bodies():
    class Hit:
        file = "Appendizitis.md"
        body = "Klinik: Druckschmerz im rechten Unterbauch."

    class Enrichment:
        claim = "Standard: drei Trokare, 10 mm supraumbilikal."

    text = reference_support_text([Hit()], [Enrichment()])
    assert "Druckschmerz im rechten Unterbauch" in text
    assert "drei Trokare" in text


def test_grounded_rewrite_never_fires_invention():
    faithful = (
        "Die Patientin wurde stationär aufgenommen. Sonographisch zeigte sich eine vergrößerte "
        "Appendix ohne freie Flüssigkeit. Am 20.04.2026 wurde die Patientin nach unauffälligem "
        "Verlauf entlassen.\n\nDiagnosen:\nAkute Appendizitis"
    )
    result = rule_checker.check(faithful, "arztbrief", DICTATION)
    assert "R-INVENT" not in _hard_ids(result), [f.rule_id for f in result.hard]


# --------------------------------------------------------------------------- prompt contract


def test_operationsbericht_prompt_allows_reference_grounded_routine_steps():
    """(a) With REFERENZWISSEN present, the OP-Bericht prompt must say routine steps may
    come from the reference instead of forbidding all non-dictated content."""
    bundle = prompt_assembly.build_prompt(
        doc_type="operationsbericht",
        dictation=DICTATION,
        enrichment=[
            {
                "statement": "Nach Team-Time-out erfolgt die Hautdesinfektion und die sterile Abdeckung.",
                "source": "Cholezystektomie.md",
                "kind": "technique",
            }
        ],
    )
    assert prompt_assembly.CONTENT_GROUNDING_HEADER in bundle.system
    assert "STANDARDWISSEN ZUM VERFAHREN" in bundle.system
    assert "bei einem Operationsbericht erlaubt und erwartet" in bundle.system
    assert "REFERENZWISSEN" in bundle.system
    assert "Routine-Schritte zu vervollständigen" in bundle.system
    # the reference knowledge itself reaches the user prompt
    assert "REFERENZWISSEN (generisch" in bundle.user
    assert "Team-Time-out" in bundle.user

    # (a2) even with enrichment OFF every OP-Bericht carries the department standard — it is
    # method knowledge, not optional web enrichment. This dictation (appendicitis) selects the
    # generic catalogue, so THE completion directive is grounded and no REFERENZWISSEN block
    # reaches the user prompt.
    plain = prompt_assembly.build_prompt(doc_type="operationsbericht", dictation=DICTATION)
    assert prompt_assembly.CONTENT_GROUNDING_HEADER in plain.system
    assert "ABTEILUNGSSTANDARD-Block" in plain.system
    assert "lassen Sie den Schritt weg, statt ihn zu erfinden" not in plain.system
    assert standards.STANDARD_HEADER in plain.user
    assert plain.standard_files == ["op-standardschritte.md"]
    assert "REFERENZWISSEN (generisch" not in plain.user


def test_non_operationsbericht_without_reference_keeps_the_forbidden_completion_directive():
    """Only the OP-Bericht gets a standard; a reference-less Arztbrief keeps the strict rule."""
    plain = prompt_assembly.build_prompt(doc_type="arztbrief", dictation=DICTATION)
    assert "SOFERN ein eingeblendeter Musterbrief sie belegt" in plain.system
    assert "REFERENZWISSEN-Block" not in plain.system
    assert standards.STANDARD_HEADER not in plain.user
    assert plain.standard_files == []


# --------------------------------------------------------------------------- per-type default


def test_per_type_enrichment_default(monkeypatch):
    """(b) OP-Bericht defaults to enrichment ON, other types stay off, overridable."""
    from briefato.research import (
        ENRICH_DEFAULT_DOC_TYPES,
        enrich_default_for,
        enrich_default_source,
    )

    monkeypatch.delenv("BRIEFATO_ENRICH_DEFAULT", raising=False)
    monkeypatch.delenv("BRIEFATO_ENRICH_DEFAULT_OPERATIONSBERICHT", raising=False)
    assert "operationsbericht" in ENRICH_DEFAULT_DOC_TYPES
    assert enrich_default_for("operationsbericht") is True
    assert enrich_default_for("zusammenfassung") is False
    assert enrich_default_source("operationsbericht") == "doc_type_default"
    assert enrich_default_source("zusammenfassung") == "off"

    # the global switch turns enrichment on for every type
    monkeypatch.setenv("BRIEFATO_ENRICH_DEFAULT", "true")
    assert enrich_default_for("zusammenfassung") is True
    assert enrich_default_source("zusammenfassung") == "global_env"

    # a per-type override wins over the global default
    monkeypatch.setenv("BRIEFATO_ENRICH_DEFAULT_OPERATIONSBERICHT", "false")
    assert enrich_default_for("operationsbericht") is False
    assert enrich_default_source("operationsbericht") == "per_type_env"


# --------------------------------------------------------------------------- R-REFERENZ is soft


def test_reference_note_is_soft_and_never_blocks_the_letter():
    """(d) A reference-grounded routine step is the soft R-REFERENZ note and never a
    correction/retry: the letter is ok and no hard instruction is produced."""
    result = rule_checker.check(OUTPUT, "operationsbericht", DICTATION, reference=REFERENCE)
    assert result.ok is True, [(f.rule_id, f.evidence) for f in result.hard]
    reference_notes = [f for f in result.findings if f.rule_id == "R-REFERENZ"]
    assert reference_notes, [f.rule_id for f in result.findings]
    assert all(f.severity == "soft" for f in reference_notes)
    assert result.correction_instructions() == []
    assert "R-REFERENZ" not in prompt_assembly.correction_block(result.correction_instructions())

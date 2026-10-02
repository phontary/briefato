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

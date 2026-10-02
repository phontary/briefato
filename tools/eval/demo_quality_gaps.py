#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused demo for the quality-gap fixes exposed by the first real-model run.

Prints the REAL module output:
  1. R-INVENT findings for the two judge-flagged sentences
     (ambulant-02 and opbericht-01),
  2. the R6 umlaut autofix on stationaer/Fluessigkeit and its no-op on
     Aerosol/Museum/Oesophagus,
  3. the triage decision for a dictation containing 'Malignitätsnachweis',
  4. the broadened R5 label detection and the targeted retry instruction.

Run::

    cd /workspace/briefato && .venv/bin/python tools/eval/demo_quality_gaps.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]
APP_DIR = REPO_ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from briefato.brain.prompt_assembly import correction_block  # noqa: E402
from briefato.brain.rule_checker import autofix_umlauts, check  # noqa: E402
from briefato.brain import triage  # noqa: E402

AMBULANT02_DICTATION = (
    "Das Kind stellte sich in Begleitung seiner Mutter in der NFA vor, nachdem es sich beim Spielen "
    "den Kopf gestossen hatte. In der KU zeigte sich an der Stirn oberhalb der linken Augenbraue eine "
    "ca. 0,5 cm grosse Kopfplatzwunde; neurologisch war das Kind unauffaellig.\n\n"
    "Die Wunde wurde desinfiziert, mit Fibrinkleber adaptiert und mit Pflaster verbunden. Die Mutter "
    "wurde über das weitere Vorgehen aufgeklaert; der Hautkleber löst sich nach etwa 3 Tagen von selbst. "
    "Eine stationaere Aufnahme war nicht erforderlich.\n\n"
    "Diagnosen:\nPlatzwunde der Stirn\nCommotio cerebri ausgeschlossen"
)

OPBERICHT01_DICTATION = (
    "OP-Bericht. Bei der 54-jaehrigen Patientin besteht eine symptomatische Cholezystolithiasis ohne "
    "Anhalt fuer eine Gallenwegsobstruktion. Bei symptomatischem Steinleiden erfolgte die geplante "
    "laparoskopische Cholezystektomie. OP: OP am 23.09.2026: laparoskopische Cholezystektomie. "
    "Intraoperativ zeigte sich eine chronisch entzuendete Gallenblase mit multiplen Konkrementen. "
    "Präparat: Gallenblase, Präparat ad Histologie. Diagnosen: Symptomatische Cholezystolithiasis "
    "Operation: Laparoskopische Cholezystektomie"
)


def _line(char: str = "=", width: int = 84) -> None:
    print(char * width)


def _show_invent(label: str, text: str, doc_type: str, source: str) -> None:
    _line("-")
    print(label)
    result = check(text, doc_type, source)
    findings = [f for f in result.findings if f.rule_id == "R-INVENT"]
    print(f"  R-INVENT findings: {len(findings)}  (hart: {len(result.hard)})")
    for finding in findings:
        print(f"    severity : {finding.severity}")
        print(f"    message  : {finding.message}")
        print(f"    evidence : {finding.evidence!r}")


def main() -> int:
    _line()
    print("BRIEFATO — DEMO der Quality-Gap-Fixes (erster Echt-Modelllauf 02.10.2026)")
    _line()

    print("1) R-INVENT — Anti-Erfindung (Quellenbindung)")
    _show_invent(
        "Fall ambulant-02: erfundener Empfehlungssatz (Judge no_invention = 1/5)",
        "Das Kind stellte sich in Begleitung seiner Mutter in der NFA vor.\n\n"
        "Empfohlen werden die regelmäßige Wundkontrolle sowie die Wiedervorstellung bei Rötung, "
        "Schwellung, zunehmenden Schmerzen oder Fieber.\n\nDiagnosen:\nPlatzwunde der Stirn",
        "ambulant",
        AMBULANT02_DICTATION,
    )
    _show_invent(
        "Fall opbericht-01: erfundener OP-Standardablauf (Judge no_invention = 0/5)",
        "Bei der 54-jährigen Patientin besteht eine symptomatische Cholezystolithiasis.\n\n"
        "Nach Team-Time-out erfolgt die Hautdesinfektion gefärbt sowie die sterile Abdeckung des Abdomens.\n\n"
        "Diagnosen:\nSymptomatische Cholezystolithiasis\n\nOperation:\nLaparoskopische Cholezystektomie",
        "operationsbericht",
        OPBERICHT01_DICTATION,
    )
    _show_invent(
        "Kontrolle: eine belegte Umformulierung (Synonyme aufgenommen/aufnahme) darf NICHT feuern",
        "Die Aufnahme der Patientin erfolgte bei Unterbauchschmerzen. Sonographisch zeigte sich eine "
        "entzündlich verdickte Sigma-Schlinge. Eine Leukozytose und ein erhöhtes CRP bestanden.",
        "arztbrief",
        "Die Patientin wurde mit Unterbauchbeschwerden stationär aufgenommen. Sonographisch zeigte sich "
        "eine entzündlich verdickte Sigma-Schlinge. Laborchemisch bestanden eine Leukozytose und ein "
        "erhöhtes CRP. Wir nahmen die Patientin zur intravenösen Antibiotikatherapie stationär auf.",
    )

    print()
    print("2) R6-AUTOFIX — deterministische Umlaut-Korrektur")
    fixed, replacements = autofix_umlauts(
        "Die Patientin wurde stationaer aufgenommen; es zeigte sich freie Fluessigkeit."
    )
    print(f"  vorher : Die Patientin wurde stationaer aufgenommen; es zeigte sich freie Fluessigkeit.")
    print(f"  nachher: {fixed}")
    print(f"  ersetzt: {replacements}")
    keep = "Das Aerosol, der Oesophagus und das Museum bleiben unverändert."
    kept, no_reps = autofix_umlauts(keep)
    print(f"  no-op  : {kept!r} (ersetzt: {no_reps})")

    print()
    print("3) TRIAGE — 'Malignitätsnachweis' bleibt klinisch")
    for dictation in (
        "Stationärer Entlassbrief mit Malignitätsnachweis in der Histologie.",
        "Bitte den KV-Nachweis zur Weiterbildung erstellen.",
    ):
        decision = triage.triage(dictation)
        print(f"  {decision.doc_type:28} <- {dictation}")

    print()
    print("4) R5 — erweiterte Label-Erkennung + gezielter Retry-Hinweis")
    r5 = check("Abschließende Kontrolle auf intraabdominelle Bluttrockenheit, welche besteht.", "operationsbericht", "")
    print(f"  R5 findings: {[f.message for f in r5.findings if f.rule_id == 'R5']}")
    retry = correction_block(
        [
            "R-INVENT: Unbelegte/erfundene Angabe (nicht im Diktat): wundkontrolle, wiedervorstellung, "
            "roetung (Fundstelle: 'Empfohlen werden die regelmäßige Wundkontrolle …')",
            "R6: ASCII-Umlaut statt ä/ö/ü: „stationaer“",
        ]
    )
    print("  --- Retry-Block (Auszug) ---")
    for line in retry.splitlines():
        print(f"    | {line}")
    _line()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

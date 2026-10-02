#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demo: department OP standards — selection, injected skeleton, grounding.

Owner: WORKSTREAM-OP-STANDARDS. Offline (no model, no DB, no network).

Prints, for an OP-Bericht dictation (laparoscopic cholecystectomy and Narbenhernie/Sublay):

  1. the department standard selected by the trigger keywords,
  2. the rendered ``ABTEILUNGSSTANDARD`` block as it reaches the prompt,
  3. the rule-checker findings for a standard-step paragraph — without the standard as
     reference it is a hard ``R-INVENT``; with the injected standard it is the soft
     ``R-REFERENZ`` note (never a hard invention).

Run::

    cd /workspace/briefato && .venv/bin/python -m briefato.brain.demo_standards
    # or
    cd /workspace/briefato && .venv/bin/python app/briefato/brain/demo_standards.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parents[2]  # .../briefato/app
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

_TMP = tempfile.mkdtemp(prefix="briefato-demo-standards-")
os.environ.setdefault("BRIEFATO_DATA_DIR", _TMP)
os.environ.setdefault("BRIEFATO_DB_URL", f"sqlite:///{Path(_TMP) / 'demo.db'}")
os.environ.setdefault("BRIEFATO_LLM_MOCK", "true")
os.environ.setdefault("BRIEFATO_SECRET_KEY", "demo-secret")

from briefato.brain import standards  # noqa: E402
from briefato.brain.prompt_assembly import build_prompt, reference_support_text  # noqa: E402
from briefato.brain.rule_checker import check as rule_check  # noqa: E402

CHE_DICTATION = (
    "OP-Bericht.\n\n"
    "Bei der 54-jährigen Patientin besteht eine symptomatische Cholezystolithiasis ohne Anhalt "
    "für eine Gallenwegsobstruktion. Bei symptomatischem Steinleiden erfolgte die geplante "
    "laparoskopische Cholezystektomie.\n\n"
    "OP:\nOP am 23.09.2026: laparoskopische Cholezystektomie. Intraoperativ zeigte sich eine "
    "chronisch entzündete Gallenblase mit multiplen Konkrementen.\n\n"
    "Präparat:\nGallenblase, Präparat ad Histologie.\n\n"
    "Diagnosen:\nSymptomatische Cholezystolithiasis\n\n"
    "Operation:\nLaparoskopische Cholezystektomie"
)

NARBEN_DICTATION = (
    "OP-Bericht.\n\n"
    "Bei dem 68-jährigen Patienten besteht eine Narbenhernie nach Medianlaparotomie mit "
    "zunehmender Größe und Beschwerden. Die operative Versorgung erfolgte mittels Sublay-Technik "
    "und Netzimplantation 15 x 20 cm.\n\n"
    "OP:\nOP am 29.09.2026: Narbenhernienversorgung in Sublay-Technik. Intraoperativ zeigte sich "
    "eine ca. 6 cm große Narbenhernie ohne Inkarzeration.\n\n"
    "Diagnosen:\nNarbenhernie nach Medianlaparotomie\n\n"
    "Operation:\nNarbenhernienversorgung in Sublay-Technik"
)


def _rule(bar: str = "=", width: int = 88) -> None:
    print(bar * width)


def _section(title: str) -> None:
    print()
    _rule("-")
    print(title)
    _rule("-")


def _print_case(label: str, dictation: str, routine: str, diagnosen: str, operation: str) -> None:
    entry = standards.select("operationsbericht", dictation)
    bundle = build_prompt(doc_type="operationsbericht", dictation=dictation)

    _section(f"FALL {label}")
    print("1) Auswahl (Trigger-Auswahl aus brain/standards/index.md)")
    print(f"   gewählter Standard    : {entry.file if entry else '(keiner)'}")
    print(f"   Fallback              : {bool(entry and entry.fallback)}")
    print(f"   bundle.standard_files : {bundle.standard_files}")
    print(f"   Block im Prompt       : {standards.STANDARD_HEADER in bundle.user}")

    print()
    print("2) Gerenderter ABTEILUNGSSTANDARD-Block (wie im Prompt)")
    block = standards.standard_block("operationsbericht", dictation)
    for line in block.splitlines():
        print(f"   | {line}")

    print()
    print("3) Findings für den Standard-Schritt-Absatz")
    from briefato.brain.rule_checker import autofix_umlauts

    draft = f"{dictation}\n\n{routine}\n\nDiagnosen:\n{diagnosen}\n\nOperation:\n{operation}"
    # Same order as the real pipeline: umlaut autofix, then the deterministic check.
    cleaned, fixes = autofix_umlauts(draft)
    without = rule_check(cleaned, "operationsbericht", dictation, autofix=fixes)
    reference = reference_support_text([], None, doc_type="operationsbericht", dictation=dictation)
    with_ref = rule_check(cleaned, "operationsbericht", dictation, autofix=fixes, reference=reference)
    print(f"   Satz                  : {routine}")
    print(f"   ohne Referenz  hard={sorted({f.rule_id for f in without.hard})}")
    print(f"   mit Standard   hard={sorted({f.rule_id for f in with_ref.hard})} "
          f"soft={sorted({f.rule_id for f in with_ref.soft})}")
    soft_msg = next((f.message for f in with_ref.soft if f.rule_id == "R-REFERENZ"), "")
    print(f"   R-REFERENZ            : {soft_msg or '(keine)'}")


def _pipeline_probe() -> None:
    """Run the REAL pipeline (mock model, enrich OFF) and show the block reached the prompt."""
    from datetime import date

    from briefato.db import SessionLocal, init_db
    from briefato.models import Patient, Subscription, User
    from briefato.pipeline import generate as gen_mod
    from briefato.pipeline.providers import MockProvider

    class _Spy:
        def __init__(self) -> None:
            self.inner = MockProvider()
            self.last_user = ""
            self.last_system = ""

        def generate(self, system: str, user: str, *, max_tokens: int = 2000, temperature: float = 0.2):
            self.last_user = user
            self.last_system = system
            return self.inner.generate(system, user, max_tokens=max_tokens, temperature=temperature)

    init_db()
    db = SessionLocal()
    try:
        user = User(
            email="demo-standards@briefato.test",
            password_hash="x",
            full_name="Dr. Demo",
            practice_name="Praxis Demo",
            street="Musterweg 1",
            zip="12345",
            city="Musterstadt",
            ui_lang="de",
        )
        db.add(user)
        db.commit()
        patient = Patient(
            user_id=user.id,
            first_name="Anna",
            last_name="Muster",
            birth_date=date(1972, 3, 1),
            sex="w",
            insurance="AOK",
            insurance_number="A123456789",
        )
        db.add(patient)
        db.add(Subscription(user_id=user.id, plan_code="klinik", letters_quota=400, letters_used=0))
        db.commit()

        spy = _Spy()
        real_get_provider = gen_mod.get_provider
        gen_mod.get_provider = lambda settings: spy
        try:
            letter = gen_mod.generate_letter(
                db,
                user=user,
                patient=patient,
                kind="operationsbericht",
                dictation=CHE_DICTATION,
                letterhead={},
                enrich=False,  # enrichment explicitly OFF: the standard must still be present
            )
        finally:
            gen_mod.get_provider = real_get_provider

        last = getattr(letter, "last_check", {}) or {}
        hard = sorted({f["rule_id"] for c in last.get("checks", []) for f in c["findings"] if f["severity"] == "hard"})
        soft = sorted({f["rule_id"] for c in last.get("checks", []) for f in c["findings"] if f["severity"] == "soft"})
        print(f"   enrich=OFF, Block im Provider-Prompt : {standards.STANDARD_HEADER in spy.last_user}")
        print(f"   Anreicherung aktiv                   : {(last.get('enrichment') or {}).get('enabled')}")
        print(f"   Findings                             : hard={hard} soft={soft}")
    finally:
        db.close()


def main() -> int:
    _rule()
    print("ABTEILUNGSSTANDARDS OPERATIONSBERICHT — Demo der Auswahl und Erdung")
    _rule()
    _print_case(
        "opbericht-01 — laparoskopische Cholezystektomie",
        CHE_DICTATION,
        "Nach Team-Time-out erfolgte die Hautdesinfektion sowie die sterile Abdeckung des Abdomens.",
        diagnosen="Symptomatische Cholezystolithiasis",
        operation="Laparoskopische Cholezystektomie",
    )
    _print_case(
        "opbericht-02 — Narbenhernie, Sublay-Netzplastik",
        NARBEN_DICTATION,
        "Nach Team-Time-out erfolgte die Hautdesinfektion sowie die sterile Abdeckung des OP-Gebiets.",
        diagnosen="Narbenhernie nach Medianlaparotomie",
        operation="Narbenhernienversorgung in Sublay-Technik",
    )

    _section("PIPELINE-PROBE — generate_letter (Mock-Modell, enrich AUS)")
    _pipeline_probe()

    print()
    _rule()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

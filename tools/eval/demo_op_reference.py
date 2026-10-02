#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused demo: per-type enrichment default + reference-grounded routine steps (OP-Bericht).

Runs the two OP-Bericht eval cases through the REAL pipeline (mock provider, offline) with
the per-document-type enrichment default active and prints:

  1. the enrichment decision actually made (enabled / source / per-type default),
  2. the relevant section of the rendered system prompt (the two-category grounding
     contract) and whether REFERENZWISSEN reached the user prompt,
  3. the deterministic rule findings and must_contain coverage,
  4. proof that a standard routine step is R-INVENT without a reference but only a soft
     R-REFERENZ note with the case's ``allowed_reference``.

Run::

    cd /workspace/briefato && .venv/bin/python tools/eval/demo_op_reference.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]
APP_DIR = REPO_ROOT / "app"
EVAL_DIR = HERE.parent
for _path in (str(APP_DIR), str(EVAL_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

_TMP = tempfile.mkdtemp(prefix="briefato-demo-op-")
os.environ["BRIEFATO_DATA_DIR"] = _TMP
os.environ["BRIEFATO_DB_URL"] = f"sqlite:///{Path(_TMP) / 'demo.db'}"
os.environ["BRIEFATO_LLM_MOCK"] = "true"
os.environ["BRIEFATO_SECRET_KEY"] = "demo-secret"
os.environ["BRIEFATO_ENV"] = "dev"
os.environ.pop("BRIEFATO_ENRICH_DEFAULT", None)
os.environ.pop("BRIEFATO_ENRICH_DEFAULT_OPERATIONSBERICHT", None)

from briefato import security  # noqa: E402
from briefato.brain.prompt_assembly import CONTENT_GROUNDING_HEADER  # noqa: E402
from briefato.brain.rule_checker import check as rule_check  # noqa: E402
from briefato.db import SessionLocal, init_db  # noqa: E402
from briefato.models import Patient, Subscription, User  # noqa: E402
from briefato.pipeline import generate as gen_mod  # noqa: E402

from eval_checks import check_must_contain  # noqa: E402
from eval_corpus import load_cases  # noqa: E402

LETTERHEAD = {
    "practice_name": "Praxis Dr. Beispiel",
    "full_name": "Dr. med. Beispiel",
    "street": "Musterweg 1",
    "zip": "12345",
    "city": "Musterstadt",
}


class _SpyProvider:
    """Wrap the offline MockProvider and record the last prompt actually rendered."""

    def __init__(self) -> None:
        from briefato.pipeline.providers import MockProvider

        self._inner = MockProvider()
        self.calls = 0
        self.last_system = ""
        self.last_user = ""

    def generate(self, system: str, user: str, *, max_tokens: int = 2000, temperature: float = 0.2):
        self.calls += 1
        self.last_system = system
        self.last_user = user
        return self._inner.generate(system, user, max_tokens=max_tokens, temperature=temperature)


def _line(char: str = "=", width: int = 88) -> None:
    print(char * width)


def _seed(db):
    user = User(
        email="demo-op@briefato-eval.test",
        password_hash="x",
        full_name="Dr. med. Beispiel",
        practice_name="Praxis Dr. Beispiel",
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
    return user, patient


def main() -> int:
    init_db()
    cases = {case.id: case for case in load_cases(only=["opbericht-01", "opbericht-02"])}
    db = SessionLocal()
    try:
        user, patient = _seed(db)
        for case_id in ("opbericht-01", "opbericht-02"):
            case = cases[case_id]
            provider = _SpyProvider()
            gen_mod.get_provider = lambda settings, _p=provider: _p

            letter = gen_mod.generate_letter(
                db,
                user=user,
                patient=patient,
                kind=case.doc_type,
                dictation=case.dictation,
                letterhead=dict(LETTERHEAD),
            )
            content = security.decrypt_field(letter.content_enc) or ""
            last = letter.last_check
            enrichment = last.get("enrichment", {})

            _line()
            print(f"FALL {case_id} — {case.title}")
            _line()
            print("1) Anreicherung (per-Dokumenttyp-Default)")
            print(f"   enabled          : {enrichment.get('enabled')}")
            print(f"   source           : {enrichment.get('source')}")
            print(f"   doc_type_default : {enrichment.get('doc_type_default')}")
            print(f"   items            : {len(enrichment.get('items') or [])}")
            print(f"   sources          : {enrichment.get('sources')}")
            print(f"   ui_note          : {enrichment.get('ui_note')!r}")

            print()
            print("2) Gerenderter Prompt — Relevanter Abschnitt (System)")
            for line in provider.last_system.splitlines():
                if any(
                    token in line
                    for token in ("INHALT:", "PATIENTENBEZOGENE", "STANDARDWISSEN", "Operationsbericht")
                ):
                    print(f"   | {line}")
            has_reference = "REFERENZWISSEN (generisch" in provider.last_user
            print(f"   REFERENZWISSEN im User-Prompt: {has_reference}")
            print(f"   Grounding-Header im System   : {CONTENT_GROUNDING_HEADER in provider.last_system}")

            print()
            print("3) Regel-Findings / Abdeckung (Mock-Maschinenschritt)")
            print(f"   retried   : {last.get('retried')}   model_calls: {last.get('model_calls')}")
            print(f"   hard      : {last.get('hard_count')} {sorted({f['rule_id'] for c in last['checks'] for f in c['findings'] if f['severity'] == 'hard'})}")
            print(f"   soft      : {last.get('soft_count')} {sorted({f['rule_id'] for c in last['checks'] for f in c['findings'] if f['severity'] == 'soft'})}")
            containment = check_must_contain(content, list(case.must_contain))
            print(f"   must_contain: {len(containment.matched)}/{containment.total}  fehlt: {containment.missing}")

            print()
            print("4) Standard-Routine-Schritt im Brieftext: mit/ohne Referenz")
            routine_step = (
                "Nach Team-Time-out erfolgte die Hautdesinfektion sowie die sterile Abdeckung."
            )
            letter_with_step = f"{case.dictation}\n\n{routine_step}\n\nDiagnosen:"
            without = rule_check(letter_with_step, case.doc_type, case.dictation)
            with_ref = rule_check(
                letter_with_step, case.doc_type, case.dictation, reference=case.allowed_reference
            )
            print(f"   ohne Referenz: R-INVENT hard={sorted({f.rule_id for f in without.hard})} "
                  f"soft={sorted({f.rule_id for f in without.soft})}")
            print(f"   mit Referenz : R-INVENT hard={sorted({f.rule_id for f in with_ref.hard})} "
                  f"soft={sorted({f.rule_id for f in with_ref.soft})}")
        _line()
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

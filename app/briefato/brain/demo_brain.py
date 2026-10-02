#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brain self-check demo — real triage, retrieval, generation and rule checking.

Run it::

    cd /workspace/briefato && .venv/bin/python app/briefato/brain/demo_brain.py

It takes a realistic German ward dictation (stationary discharge letter), prints

  1. the triage decision,
  2. the retrieved Musterbriefe with scores,
  3. the generated text (offline MockProvider — no network),
  4. the deterministic checker findings,

then runs the checker once more on a hand-written, compliant Arztbrief to show a
clean pass. Everything printed is the real module output.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
APP_DIR = HERE.parents[2]  # app/briefato/brain/demo_brain.py -> app/
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

_TMP = tempfile.mkdtemp(prefix="briefato-brain-demo-")
os.environ.setdefault("BRIEFATO_DATA_DIR", _TMP)
os.environ.setdefault("BRIEFATO_DB_URL", f"sqlite:///{Path(_TMP) / 'demo.db'}")
os.environ.setdefault("BRIEFATO_LLM_MOCK", "true")
os.environ.setdefault("BRIEFATO_SECRET_KEY", "demo-secret")
os.environ.setdefault("BRIEFATO_ENV", "dev")

from briefato import security  # noqa: E402
from briefato.brain import brain_loader, retrieval, triage  # noqa: E402
from briefato.brain.rule_checker import check  # noqa: E402
from briefato.db import SessionLocal, init_db  # noqa: E402
from briefato.models import Patient, Subscription, User  # noqa: E402
from briefato.pipeline.generate import generate_letter  # noqa: E402

DICTATION = (
    "Patientin Anna Müller, geboren am 02.03.1974. Seit drei Tagen rechtsseitige "
    "Oberbauchschmerzen mit Ausstrahlung in die rechte Schulter, Nausea, subfebrile "
    "Temperaturen. Sonographie: Cholelithiasis mit verdickter Gallenblasenwand, kein "
    "freier Flüssigkeitssaum. Labor: CRP 87, Leukozyten 14,2. Wir nahmen die Patientin "
    "zur weiteren Diagnostik bzw. Schmerztherapie stationär auf. Am 17.04.2026 "
    "laparoskopische Cholezystektomie bei gedeckt perforierter Cholezystitis, "
    "intraoperativ keine Gallenwegsobstruktion. Postoperativ regelrechter Verlauf, "
    "Kostaufbau vertragen, Wundverhältnisse reizlos. Entlassung am 21.04.2026 in die "
    "häusliche Pflege."
)


def _line(char: str = "=", width: int = 78) -> None:
    print(char * width)


def main() -> int:
    _line()
    print("BRIEFATO BRAIN DEMO —", brain_loader.status()["brain_dir"])
    print(
        f"brain {brain_loader.status()['brain_version']} | "
        f"{len(brain_loader.rules())} Regeln | "
        f"{len(brain_loader.anti_pattern_lines())} Anti-Patterns | "
        f"{brain_loader.status()['templates']} Musterbriefe"
    )
    _line()

    # 1) triage ---------------------------------------------------------------
    decision = triage.triage(DICTATION)
    _line("-")
    print("1) TRIAGE")
    print(f"   doc_type   : {decision.doc_type} ({decision.doc_types})")
    print(f"   confidence : {decision.confidence}")
    print(f"   reason     : {decision.reason}")
    print(f"   signals    : {decision.signals}")

    # 2) retrieval ------------------------------------------------------------
    masked = " ".join(DICTATION.split(" ")[:80])
    hits = retrieval.retrieve(masked, limit=5)
    _line("-")
    print("2) RETRIEVED MUSTERBRIEFE (Top-5)")
    for rank, hit in enumerate(hits, 1):
        flag = " [reference_only]" if hit.reference_only else ""
        print(f"   {rank}. [{hit.score:>6.3f}] {hit.title}  ({hit.file}){flag}")
        print(f"        Sektionen: {', '.join(hit.sections_present)}")
    print(f"   scrub-pending ausgeschlossen: {sorted(retrieval.SCRUB_PENDING)}")

    # 3) generation (offline mock) -------------------------------------------
    init_db()
    session = SessionLocal()
    try:
        suffix = os.urandom(4).hex()
        user = User(
            email=f"demo-{suffix}@praxis-test.de",
            password_hash="x",
            full_name="Dr. med. Weber",
            practice_name="Praxis Dr. Weber",
            street="Hauptstraße 1",
            zip="10115",
            city="Berlin",
            phone="030 5551234",
            tax_id="12/345/67890",
            ui_lang="de",
        )
        session.add(user)
        session.commit()
        patient = Patient(
            user_id=user.id,
            first_name="Anna",
            last_name="Müller",
            sex="w",
            birth_date=__import__("datetime").date(1974, 3, 2),
        )
        session.add(patient)
        session.add(Subscription(user_id=user.id, plan_code="starter", letters_quota=40))
        session.commit()

        letter = generate_letter(
            session,
            user=user,
            patient=patient,
            kind="arztbrief",
            dictation=DICTATION,
            letterhead={"practice_name": "Praxis Dr. Weber", "full_name": "Dr. med. Weber"},
        )
        content = security.decrypt_field(letter.content_enc)
        _line("-")
        print("3) GENERATED LETTER (MockProvider) — status:", letter.status, "| kind:", letter.kind)
        print(f"   letter.error: {letter.error or '(leer)'}")
        print("   ---- text ----")
        for line in content.splitlines():
            print("   | " + line)

        last = getattr(letter, "last_check", None) or {}
        _line("-")
        print("4) CHECKER FINDINGS")
        print(f"   hard={last.get('hard_count')} soft={last.get('soft_count')} retried={last.get('retried')}")
        for block in last.get("checks", []):
            print(f"   [{block['doc_type']}] {block['summary']}")
            for finding in block["findings"]:
                print(f"      {finding['severity']:<4} {finding['rule_id']:<6} {finding['message']}"
                      + (f" | {finding['evidence']!r}" if finding['evidence'] else ""))
    finally:
        session.close()

    # 4b) checker on a compliant draft ---------------------------------------
    compliant = (
        "Die Patientin stellte sich mit dem Rettungsdienst bei seit vier Wochen bestehender "
        "atraumatischer Ulzeration am rechten Unterschenkel vor. Wir nahmen die Patientin zur "
        "weiteren Diagnostik bzw. Schmerztherapie stationär auf.\n"
        "In der KU zeigte sich eine 3 × 3 cm große Ulzeration mit fibrinbelegtem Wundgrund, die "
        "peripheren Pulse waren tastbar.\n"
        "Zur Abklärung erfolgte eine Duplexsonographie, wobei sich eine chronisch venöse "
        "Insuffizienz ohne Thrombusnachweis zeigte.\n"
        "Im Verlauf gestaltete sich die Wundheilung regelrecht, der Kostaufbau wurde vertragen.\n"
        "Nach klinischer Besserung entließen wir die Patientin am 07.05.2026 in die häusliche Pflege.\n\n"
        "ambulante Therapieempfehlungen nach der Entlassung:\n"
        "Wir empfahlen die regelmäßige Wundkontrolle und ausreichende Mobilisation. Vielen Dank "
        "für die Weiterbetreuung.\n\n"
        "Diagnosen:\n"
        "Ulcus cruris venosum\n"
        "Chronisch venöse Insuffizienz\n\n"
        "Nebenerkrankungen:\n"
        "keine\n\n"
        "Therapie-Maßnahmen auf der Station:\n"
        "OP am 17.04.2026: Wunddébridement\n"
        "Kompressionstherapie"
    )
    clean = check(compliant, "arztbrief", "Ulcus cruris venosum")
    _line("-")
    print("4b) CHECKER auf einem regelkonformen Arztbrief")
    print(f"   ok={clean.ok} | {clean.summary}")
    _line()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

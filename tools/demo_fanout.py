#!/usr/bin/env python3
"""Briefato ENGINE-V2 demo — a realistic 14-source Entlassbrief through the whole engine.

Runs the fan-out pipeline (segment → bounded-parallel compression → weave) with the >5-source
routing rule and the grounded archive enrichment against the deterministic, fully offline
mock provider, and prints everything the workstream must show:

    routing decision · the 14 segments · per-segment compression results · the weave output ·
    the rule-check result · the enrichment list (with sources) · model calls & concurrency.

Run (no network, mock provider)::

    cd /workspace/briefato && BRIEFATO_LLM_MOCK=true \\
        .venv/bin/python tools/demo_fanout.py [--max-parallel 3]
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "app"
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

WORKDIR = Path(tempfile.mkdtemp(prefix="briefato-fanout-demo-"))
os.environ["BRIEFATO_DATA_DIR"] = str(WORKDIR)
os.environ["BRIEFATO_DB_URL"] = f"sqlite:///{WORKDIR / 'demo.db'}"
os.environ["BRIEFATO_LLM_MOCK"] = "true"
os.environ["BRIEFATO_SECRET_KEY"] = "demo-secret"
os.environ.setdefault("BRIEFATO_ENV", "dev")

from briefato import security  # noqa: E402
from briefato.db import SessionLocal, init_db  # noqa: E402
from briefato.models import AuditEvent, Patient, Subscription, User  # noqa: E402
from briefato.pipeline.generate import generate_letter  # noqa: E402
from briefato.pipeline.segmenter import SEGMENT_LABELS  # noqa: E402

# --------------------------------------------------------------------------- fixture

# A realistic KIS-style multi-source entlassbrief stack: 14 labelled source documents,
# ASCII transliterations (as real dictations/exports arrive), form-label noise and two
# non-adjacent duplicate-labelled blocks to exercise the segmenter's robustness.
DICTATION = """KIS-Export Unfallkrankenhaus Mitte
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Briefato engine-v2 fan-out demo")
    parser.add_argument("--max-parallel", type=int, default=3, help="bounded concurrency cap (default 3)")
    parser.add_argument("--enrich", action="store_true", help="enable grounded archive enrichment")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        user = User(
            email="arzt@praxis-demo.de",
            password_hash="x",
            full_name="Dr. med. Weber",
            practice_name="Praxis Dr. Weber",
            street="Hauptstraße 1",
            zip="10115",
            city="Berlin",
            phone="030 5551234",
            tax_id="12/345/67890",
            letterhead_json={},
            ui_lang="de",
        )
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

        letter = generate_letter(
            db,
            user=user,
            patient=patient,
            kind="arztbrief",
            dictation=DICTATION,
            letterhead={"practice_name": "Praxis Dr. Weber", "full_name": "Dr. med. Weber"},
            enrich=args.enrich,
            max_parallel=args.max_parallel,
        )

        last = letter.last_check
        route = last.get("route") or {}
        compression = (last.get("compression") or [{}])[0]
        enrichment = last.get("enrichment") or {}
        checks = last.get("checks") or []
        check = checks[0] if checks else {}

        print("=== BRIEFATO ENGINE-V2 — FAN-OUT + GROUNDED ENRICHMENT DEMO ===")
        print(f"workdir            : {WORKDIR}")
        print()
        print("--- 1) ROUTING ------------------------------------------------")
        print(f"Route              : {route.get('ui_label')}")
        print(f"route              : {route.get('route')}  (doc_type={route.get('doc_type')}, "
              f"threshold >{route.get('threshold')})")
        print(f"reason             : {route.get('reason')}")
        print()
        print(f"--- 2) SOURCES ({last.get('source_count')} segments) ---------------------------")
        for seg in last.get("segments", []):
            print(f"  #{seg['index']:>2} {seg['label']:<24} conf={seg['confidence']:.2f} "
                  f"dup_of={seg['duplicate_of']} chars={seg['chars']}  <- {seg['heading']!r}")
        print()
        print(f"--- 3) PER-SEGMENT COMPRESSION (max {compression.get('max_parallel')} in flight, "
              f"peak={compression.get('peak_concurrency')}) ---")
        for item in compression.get("results", []):
            status = "ok " if item["ok"] else "GAP"
            print(f"  [{status}] #{item['index']:>2} {SEGMENT_LABELS.get(item['type'], item['type']):<22} "
                  f"attempts={item['attempts']} -> {item['text'][:110]!r}")
        print(f"  segments_total={compression.get('segments_total')} "
              f"ok={compression.get('segments_ok')} failed={compression.get('segments_failed')} "
              f"compression_calls={compression.get('compression_calls')}")
        if compression.get("gaps"):
            print(f"  GAPS (letter generated without them, reported): {compression['gaps']}")
        print()
        print("--- 4) WEAVE OUTPUT ------------------------------------------")
        print(security.decrypt_field(letter.content_enc))
        print()
        print("--- 5) RULE CHECK --------------------------------------------")
        print(f"ok={check.get('ok')}  summary={check.get('summary')!r}  retried={last.get('retried')}")
        for finding in check.get("findings", []):
            print(f"  {finding['severity']:<4} {finding['rule_id']}: {finding['message']}")
        print()
        print("--- 6) GROUNDED ENRICHMENT -----------------------------------")
        print(f"enabled={enrichment.get('enabled')}  web_available={enrichment.get('web_available')}  "
              f"blocked={enrichment.get('blocked')}")
        if enrichment.get("items"):
            print(f"ui_note: {enrichment.get('ui_note')}")
            for item in enrichment["items"]:
                print(f"  - [{item['kind']}] {item['statement'][:100]}   (Quelle: {item['source']})")
        else:
            print("  (keine Referenz-Ergänzungen)")
        print()
        print("--- 7) COST / CONCURRENCY ------------------------------------")
        print(f"model_calls        : {last.get('model_calls')} "
              f"(compression={compression.get('compression_calls')}, "
              f"weave={last.get('model_calls', 0) - (compression.get('compression_calls') or 0)})")
        print(f"max_concurrency    : {last.get('max_concurrency')} (cap {last.get('max_parallel')})")
        print(f"tokens in/out      : {letter.tokens_in} / {letter.tokens_out}")
        print()
        print("--- 8) AUDIT -------------------------------------------------")
        generated = db.query(AuditEvent).filter_by(event="letter.generated", target_id=letter.id).count()
        enriched = db.query(AuditEvent).filter_by(event="letter.enriched", target_id=letter.id).count()
        print(f"letter.generated   : {generated}")
        print(f"letter.enriched    : {enriched}")
        print(f"letter.status      : {letter.status}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""One real model call through the Briefato pipeline (synthetic data, no patient data).

Usage: .venv/bin/python tools/real_model_probe.py [--model ID] [--enrich]
Reads DEEPSEEK_API_KEY from the environment or from the Schreibdienst profile .env.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "app"
sys.path.insert(0, str(APP))

PROFILE_ENV = Path("/home/hermeswebui/.hermes/profiles/schreibdienst/.env")

TMP = tempfile.mkdtemp(prefix="briefato-real-")
os.environ.setdefault("BRIEFATO_DATA_DIR", TMP)
os.environ.setdefault("BRIEFATO_DB_URL", f"sqlite:///{Path(TMP) / 'real.db'}")
os.environ.setdefault("BRIEFATO_LLM_MOCK", "false")
os.environ.setdefault("BRIEFATO_SECRET_KEY", "real-probe-secret")
os.environ.setdefault("BRIEFATO_ENV", "staging")

DICTATION = (
    "KIS-Auszug, Pat. Muster, Anna, geb. 02.03.1974, Fall-Nr. 4711\n"
    "Anamnese: seit zwei Tagen zunehmende linksseitige Unterbauchschmerzen, kein Fieber, "
    "kein Erbrechen.\n"
    "KU: Abd. weich, DS li. UB, keine ABW, DG regelrecht, pDMS intakt.\n"
    "Labor: CRP 42 mg/l, Leukozyten 12,3/nl, Krea 0,9 mg/dl.\n"
    "Sonographie Abdomen: wandverdickte Sigma-Schlinge, kein freier Flussigkeit, keine Abszessbildung.\n"
    "CT Abdomen: V.a. akute Divertikulitis links, keine Perforation, keine freie Luft.\n"
    "Verlauf: unter kalkulierter AB-Therapie (Ceftriaxon/Metronidazol i.v.) und Schmerztherapie "
    "Rueckgang der Beschwerden, Kostaufbau ab Tag 2 problemlos, Stuhlgang spontan.\n"
    "Entlassung: beschwerdefrei, Entlassung am 08.10.2026, Kontrolle beim Hausarzt, "
    "Koloskopie in 6 Wochen empfohlen.\n"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.environ.get("BRIEFATO_LLM_MODEL", "deepseek-flash"))
    parser.add_argument("--base-url", default=os.environ.get("BRIEFATO_LLM_BASE_URL", "https://api.deepseek.com/v1"))
    parser.add_argument("--enrich", action="store_true")
    parser.add_argument("--show-prompt", action="store_true")
    args = parser.parse_args()

    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key and PROFILE_ENV.is_file():
        for line in PROFILE_ENV.read_text(encoding="utf-8").splitlines():
            if line.startswith("DEEPSEEK_API_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        print("FATAL: no DeepSeek API key found", file=sys.stderr)
        return 2
    os.environ["BRIEFATO_LLM_API_KEY"] = key

    from briefato.config import get_settings
    from briefato.db import SessionLocal, init_db
    from briefato.models import Patient, User
    from briefato import security
    from briefato.pipeline.generate import generate_letter

    get_settings.cache_clear()
    settings = get_settings()
    settings.llm_mock = False
    settings.llm_api_key = key
    settings.llm_base_url = args.base_url
    settings.llm_model = args.model

    init_db()
    db = SessionLocal()
    user = User(
        email="probe@briefato.test",
        password_hash=security.hash_password("x"),
        full_name="Dr. med. Katrin Weber",
        practice_name="Praxis Dr. Weber",
        letterhead_json={
            "practice_name": "Praxis Dr. Weber",
            "full_name": "Dr. med. Katrin Weber",
            "street": "Hauptstraße 1",
            "zip": "10115",
            "city": "Berlin",
            "phone": "030 5551234",
        },
    )
    db.add(user)
    db.commit()
    patient = Patient(
        user_id=user.id, first_name="Anna", last_name="Muster",
        insurance="AOK", insurance_number="A999888777",
    )
    db.add(patient)
    db.commit()

    print(f"model={args.model} base_url={args.base_url} enrich={args.enrich}")
    letter = generate_letter(
        db, user=user, patient=patient, kind="entlassbrief", dictation=DICTATION,
        letterhead=user.letterhead_json, enrich=args.enrich,
    )
    text = security.decrypt_field(letter.content_enc)
    detail = getattr(letter, "last_check", None)
    route = getattr(letter, "route_label", "") or ""
    print(f"status={letter.status} route={route} model={letter.model}")
    print(f"tokens_in={letter.tokens_in} tokens_out={letter.tokens_out} cost_usd={letter.cost_usd:.5f}")
    if detail is not None:
        print(f"rule_check: hard={len(getattr(detail, 'hard', []) or [])} "
              f"soft={len(getattr(detail, 'soft', []) or [])} retried={getattr(detail, 'retried', None)}")
    enrichments = getattr(letter, "enrichments", None) or []
    print(f"enrichments: {len(enrichments)}")
    for e in enrichments[:4]:
        print(f"  - [{getattr(e, 'kind', '?')}] {getattr(e, 'claim', str(e))[:110]} (Quelle: {getattr(e, 'source', '?')})")
    print("\n=== GENERATED TEXT (real model) ===")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

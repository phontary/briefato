"""Reproducible end-to-end smoke check for the Briefato letter pipeline.

Run from the repo root (no network, mock provider)::

    cd /workspace/briefato && BRIEFATO_LLM_MOCK=true \\
        .venv/bin/python app/briefato/pipeline/scripts/smoke.py

Generates one Arztbrief for a fake patient through the full flow
(pseudonymise -> provider -> restore -> encrypted storage -> DOCX) and prints the
first 400 characters of the restored German letter and the paths of the artefacts.
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[3]  # .../app
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

WORKDIR = Path(tempfile.mkdtemp(prefix="briefato-smoke-"))
os.environ["BRIEFATO_DATA_DIR"] = str(WORKDIR)
os.environ["BRIEFATO_DB_URL"] = f"sqlite:///{WORKDIR / 'smoke.db'}"
os.environ["BRIEFATO_LLM_MOCK"] = "true"
os.environ["BRIEFATO_SECRET_KEY"] = "smoke-secret"
os.environ.setdefault("BRIEFATO_ENV", "dev")

from briefato import security  # noqa: E402
from briefato.db import SessionLocal, init_db  # noqa: E402
from briefato.models import Letter, Patient, Subscription, User  # noqa: E402
from briefato.pipeline.generate import generate_letter  # noqa: E402
from briefato.pipeline.letterhead import render_docx  # noqa: E402


def main() -> int:
    init_db()
    db = SessionLocal()
    try:
        user = User(
            email="arzt@praxis-smoke.de",
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
            birth_date=date(1974, 3, 2),
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

        dictation = (
            "Patientin Anna Müller, geboren am 02.03.1974. "
            "Seit drei Tagen rechtsseitige Oberbauchschmerzen mit Ausstrahlung in die rechte Schulter, "
            "Übelkeit, kein Fieber. Sonographie: Cholelithiasis ohne Zeichen einer akuten Cholezystitis. "
            "Labor: CRP leicht erhöht, übrige Werte unauffällig. "
            "Empfehlung: Vorstellung zur laparoskopischen Cholezystektomie, Wundkontrolle nach einer Woche."
        )
        letterhead = {
            "practice_name": "Praxis Dr. Weber",
            "full_name": "Dr. med. Weber",
            "street": "Hauptstraße 1",
            "zip": "10115",
            "city": "Berlin",
            "phone": "030 5551234",
            "email": "kontakt@praxis-smoke.de",
            "tax_id": "12/345/67890",
        }

        letter: Letter = generate_letter(
            db,
            user=user,
            patient=patient,
            kind="arztbrief",
            dictation=dictation,
            letterhead=letterhead,
        )
        restored = security.decrypt_field(letter.content_enc)

        out_path = WORKDIR / "arztbrief_mueller.docx"
        render_docx(
            restored,
            letterhead,
            {
                "last_name": patient.last_name,
                "first_name": patient.first_name,
                "birth_date": patient.birth_date.strftime("%d.%m.%Y"),
                "insurance_number": patient.insurance_number,
            },
            out_path,
            "arztbrief",
        )

        print("=== Briefato pipeline smoke ===")
        print(f"status              : {letter.status}")
        print(f"title               : {letter.title}")
        print(f"model / provider    : {letter.model} / mock")
        print(f"tokens in / out     : {letter.tokens_in} / {letter.tokens_out}")
        print(f"cost_usd            : {letter.cost_usd}")
        print(f"dictation encrypted : {letter.dictation_enc[:24]}…")
        print(f"content  encrypted  : {letter.content_enc[:24]}…")
        print(f"DOCX path           : {out_path} (exists={out_path.exists()})")
        print(f"workdir             : {WORKDIR}")
        print()
        print("=== Restored German letter (first 400 chars) ===")
        print(restored[:400])
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

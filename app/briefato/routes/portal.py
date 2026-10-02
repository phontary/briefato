"""Dashboard and full-text search (tenant-scoped)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Request
from sqlalchemy import or_, select

from ..models import Letter, Patient, utcnow
from ..security import decrypt_field
from .deps import DB, CurrentUser, LETTER_KIND_LABELS, render
from .letters import _quota

router = APIRouter(prefix="/app", tags=["portal"])

_SEARCH_PATIENTS_LIMIT = 50
_SEARCH_LETTERS_SCAN_LIMIT = 500
_SEARCH_LETTERS_LIMIT = 30


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
def dashboard(request: Request, db: DB, user: CurrentUser):
    now = utcnow()
    month_start = datetime(now.year, now.month, 1)

    patient_count = len(
        db.scalars(select(Patient).where(Patient.user_id == user.id, Patient.archived_at.is_(None))).all()
    )
    letters_month = len(
        db.scalars(
            select(Letter).where(Letter.user_id == user.id, Letter.created_at >= month_start)
        ).all()
    )
    pending_approval = len(
        db.scalars(
            select(Letter).where(Letter.user_id == user.id, Letter.status == "done")
        ).all()
    )
    recent_letters = db.scalars(
        select(Letter).where(Letter.user_id == user.id).order_by(Letter.updated_at.desc()).limit(5)
    ).all()

    return render(
        request,
        "app/dashboard.html",
        counters={
            "patients": patient_count,
            "letters_month": letters_month,
            "pending_approval": pending_approval,
        },
        quota=_quota(db, user),
        recent_letters=recent_letters,
        active="dashboard",
        crumbs=[("Übersicht", None)],
    )


@router.get("/suche", include_in_schema=False)
def suche(request: Request, db: DB, user: CurrentUser, q: str | None = None):
    term = (q or "").strip()
    patients: list[Patient] = []
    letters: list[dict] = []

    if term:
        like = f"%{term}%"
        patients = db.scalars(
            select(Patient)
            .where(
                Patient.user_id == user.id,
                or_(
                    Patient.first_name.ilike(like),
                    Patient.last_name.ilike(like),
                    Patient.external_ref.ilike(like),
                    Patient.insurance.ilike(like),
                    Patient.insurance_number.ilike(like),
                    Patient.city.ilike(like),
                ),
            )
            .order_by(Patient.last_name, Patient.first_name)
            .limit(_SEARCH_PATIENTS_LIMIT)
        ).all()

        needle = term.lower()
        candidates = db.scalars(
            select(Letter)
            .where(Letter.user_id == user.id)
            .order_by(Letter.created_at.desc())
            .limit(_SEARCH_LETTERS_SCAN_LIMIT)
        ).all()
        for letter in candidates:
            hints: list[str] = []
            if needle in (letter.title or "").lower():
                hints.append("Titel")
            if needle in (LETTER_KIND_LABELS.get(letter.kind, letter.kind)).lower():
                hints.append("Art")
            if needle in decrypt_field(letter.content_enc).lower():
                hints.append("Text")
            if hints:
                letters.append({"letter": letter, "hint": " · ".join(hints)})
                if len(letters) >= _SEARCH_LETTERS_LIMIT:
                    break

    results = {
        "patients": patients,
        "letters": [{"id": item["letter"].id, "title": item["letter"].title,
                     "patient": item["letter"].patient, "status": item["letter"].status,
                     "match_hint": item["hint"]} for item in letters],
    }
    return render(
        request,
        "app/suche.html",
        q=term,
        results=results,
        total=len(patients) + len(letters),
        active="suche",
        crumbs=[("Übersicht", "/app"), ("Suche", None)],
    )

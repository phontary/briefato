"""Patient records: list, create, detail, edit, archive. Every query is tenant-scoped."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import or_, select

from ..models import Letter, Patient, utcnow
from ..security import audit, decrypt_field, encrypt_field
from ..models import new_id
from .deps import CSRF, DB, CurrentUser, get_patient_or_404, render

router = APIRouter(prefix="/app/patienten", tags=["patienten"])

_TEXT_FIELDS = (
    "external_ref",
    "first_name",
    "last_name",
    "sex",
    "insurance",
    "insurance_number",
    "street",
    "zip",
    "city",
    "phone",
    "email",
    "referring_doctor",
)


async def _form_values(request: Request) -> dict[str, str]:
    form = await request.form()
    return {field: str(form.get(field, "")).strip() for field in _TEXT_FIELDS} | {
        "birth_date": str(form.get("birth_date", "")).strip(),
        "notes": str(form.get("notes", "")),
    }


def _validate(values: dict[str, str]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not values.get("last_name"):
        errors["last_name"] = "Bitte geben Sie den Nachnamen an."
    if not values.get("first_name"):
        errors["first_name"] = "Bitte geben Sie den Vornamen an."
    birth = values.get("birth_date")
    if birth:
        try:
            date.fromisoformat(birth)
        except ValueError:
            errors["birth_date"] = "Bitte geben Sie ein gültiges Datum an (JJJJ-MM-TT)."
    return errors


def _apply(patient: Patient, values: dict[str, str]) -> None:
    for field in _TEXT_FIELDS:
        setattr(patient, field, values.get(field, "") or "")
    birth = values.get("birth_date")
    if birth:
        try:
            patient.birth_date = date.fromisoformat(birth)
        except ValueError:
            patient.birth_date = None
    else:
        patient.birth_date = None
    patient.notes_enc = encrypt_field(values.get("notes", "")) if values.get("notes", "").strip() else None


# --------------------------------------------------------------------------- list


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
def liste(request: Request, db: DB, user: CurrentUser, q: str | None = None, archiviert: int = 0):
    stmt = select(Patient).where(Patient.user_id == user.id)
    if not archiviert:
        stmt = stmt.where(Patient.archived_at.is_(None))
    term = (q or "").strip()
    if term:
        like = f"%{term}%"
        stmt = stmt.where(
            or_(
                Patient.first_name.ilike(like),
                Patient.last_name.ilike(like),
                Patient.insurance_number.ilike(like),
                Patient.external_ref.ilike(like),
                Patient.city.ilike(like),
            )
        )
    stmt = stmt.order_by(Patient.archived_at.is_not(None), Patient.last_name, Patient.first_name)
    patients = db.scalars(stmt).all()
    return render(
        request,
        "app/patienten/liste.html",
        patients=patients,
        q=term,
        archiviert=archiviert,
        active="patienten",
        crumbs=[("Übersicht", "/app"), ("Patienten", None)],
    )


# --------------------------------------------------------------------------- create


@router.get("/neu", include_in_schema=False)
def neu_form(request: Request, user: CurrentUser):
    return render(
        request,
        "app/patienten/form.html",
        patient=None,
        form={},
        errors={},
        error=None,
        heading="Patient anlegen",
        action="/app/patienten/neu",
        active="patienten",
        crumbs=[("Übersicht", "/app"), ("Patienten", "/app/patienten"), ("Neu", None)],
    )


@router.post("/neu", include_in_schema=False, dependencies=[CSRF])
async def neu_submit(request: Request, db: DB, user: CurrentUser):
    values = await _form_values(request)
    errors = _validate(values)
    if errors:
        return render(
            request,
            "app/patienten/form.html",
            patient=None,
            form=values,
            errors=errors,
            error=None,
            heading="Patient anlegen",
            action="/app/patienten/neu",
            active="patienten",
            crumbs=[("Übersicht", "/app"), ("Patienten", "/app/patienten"), ("Neu", None)],
            status_code=400,
        )
    patient = Patient(id=new_id(), user_id=user.id)
    _apply(patient, values)
    db.add(patient)
    db.commit()
    audit(db, event="patient.created", user_id=user.id, target_type="patient", target_id=patient.id, request=request)
    return RedirectResponse(f"/app/patienten/{patient.id}?m=patient_angelegt", status_code=303)


# --------------------------------------------------------------------------- detail / edit


@router.get("/{patient_id}", include_in_schema=False)
def detail(request: Request, db: DB, user: CurrentUser, patient_id: str):
    patient = get_patient_or_404(db, user, patient_id)
    letters = db.scalars(
        select(Letter)
        .where(Letter.user_id == user.id, Letter.patient_id == patient.id)
        .order_by(Letter.created_at.desc())
    ).all()
    return render(
        request,
        "app/patienten/detail.html",
        patient=patient,
        letters=letters,
        notes=decrypt_field(patient.notes_enc),
        active="patienten",
        crumbs=[("Übersicht", "/app"), ("Patienten", "/app/patienten"), (patient.display_name, None)],
    )


@router.get("/{patient_id}/bearbeiten", include_in_schema=False)
def bearbeiten_form(request: Request, db: DB, user: CurrentUser, patient_id: str):
    patient = get_patient_or_404(db, user, patient_id)
    form = {field: getattr(patient, field) or "" for field in _TEXT_FIELDS} | {
        "birth_date": patient.birth_date.isoformat() if patient.birth_date else "",
        "notes": decrypt_field(patient.notes_enc),
    }
    return render(
        request,
        "app/patienten/form.html",
        patient=patient,
        form=form,
        errors={},
        error=None,
        heading="Patient bearbeiten",
        action=f"/app/patienten/{patient.id}/bearbeiten",
        active="patienten",
        crumbs=[("Übersicht", "/app"), ("Patienten", "/app/patienten"), (patient.display_name, None), ("Bearbeiten", None)],
    )


@router.post("/{patient_id}/bearbeiten", include_in_schema=False, dependencies=[CSRF])
async def bearbeiten_submit(request: Request, db: DB, user: CurrentUser, patient_id: str):
    patient = get_patient_or_404(db, user, patient_id)
    values = await _form_values(request)
    errors = _validate(values)
    if errors:
        return render(
            request,
            "app/patienten/form.html",
            patient=patient,
            form=values,
            errors=errors,
            error=None,
            heading="Patient bearbeiten",
            action=f"/app/patienten/{patient.id}/bearbeiten",
            active="patienten",
            crumbs=[("Übersicht", "/app"), ("Patienten", "/app/patienten"), (patient.display_name, None), ("Bearbeiten", None)],
            status_code=400,
        )
    _apply(patient, values)
    db.commit()
    audit(db, event="patient.updated", user_id=user.id, target_type="patient", target_id=patient.id, request=request)
    return RedirectResponse(f"/app/patienten/{patient.id}?m=patient_gespeichert", status_code=303)


# --------------------------------------------------------------------------- archive


@router.post("/{patient_id}/archivieren", include_in_schema=False, dependencies=[CSRF])
def archivieren(request: Request, db: DB, user: CurrentUser, patient_id: str):
    patient = get_patient_or_404(db, user, patient_id)
    if patient.archived_at is None:
        patient.archived_at = utcnow()
        db.commit()
        audit(db, event="patient.archived", user_id=user.id, target_type="patient", target_id=patient.id, request=request)
    return RedirectResponse(f"/app/patienten/{patient.id}?m=patient_archiviert", status_code=303)

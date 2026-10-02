"""Account: profile, practice data, letterhead, plan view, data export, deletion request."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select, update

from ..models import AuthSession, Generation, Letter, Patient, Subscription, utcnow
from ..security import SESSION_COOKIE, audit, decrypt_field
from .deps import CSRF, DB, CurrentUser, render
from .letters import _quota

router = APIRouter(prefix="/app/konto", tags=["konto"])

_LETTERHEAD_FIELDS = ("lh_name", "lh_subtitle", "lh_address", "lh_contact", "lh_footer")
_LETTERHEAD_KEYS = ("name", "subtitle", "address", "contact", "footer")


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
def konto(request: Request, db: DB, user: CurrentUser):
    form = {
        "full_name": user.full_name,
        "phone": user.phone,
        "practice_name": user.practice_name,
        "street": user.street,
        "zip": user.zip,
        "city": user.city,
        "country": user.country,
        "tax_id": user.tax_id,
    }
    return render(
        request,
        "app/konto.html",
        form=form,
        letterhead=user.letterhead_json or {},
        quota=_quota(db, user),
        errors={},
        active="konto",
        crumbs=[("Übersicht", "/app"), ("Konto", None)],
    )


@router.post("/profil", include_in_schema=False, dependencies=[CSRF])
def profil(request: Request, db: DB, user: CurrentUser, full_name: str = Form(""), phone: str = Form("")):
    user.full_name = full_name.strip()[:200]
    user.phone = phone.strip()[:60]
    db.commit()
    audit(db, event="account.profile_updated", user_id=user.id, request=request)
    return RedirectResponse("/app/konto?m=profil_gespeichert", status_code=303)


@router.post("/praxis", include_in_schema=False, dependencies=[CSRF])
def praxis(
    request: Request,
    db: DB,
    user: CurrentUser,
    practice_name: str = Form(""),
    street: str = Form(""),
    zip: str = Form(""),
    city: str = Form(""),
    country: str = Form("DE"),
    tax_id: str = Form(""),
):
    user.practice_name = practice_name.strip()[:200]
    user.street = street.strip()[:200]
    user.zip = zip.strip()[:16]
    user.city = city.strip()[:120]
    country = country.strip().upper()[:2] or "DE"
    user.country = country
    user.tax_id = tax_id.strip()[:60]
    db.commit()
    audit(db, event="account.practice_updated", user_id=user.id, request=request)
    return RedirectResponse("/app/konto?m=profil_gespeichert", status_code=303)


@router.post("/briefkopf", include_in_schema=False, dependencies=[CSRF])
async def briefkopf(request: Request, db: DB, user: CurrentUser):
    form = await request.form()
    letterhead = dict(user.letterhead_json or {})
    for field, key in zip(_LETTERHEAD_FIELDS, _LETTERHEAD_KEYS):
        letterhead[key] = str(form.get(field, "")).strip()[:300]
    user.letterhead_json = letterhead
    db.commit()
    audit(db, event="account.letterhead_updated", user_id=user.id, request=request)
    return RedirectResponse("/app/konto?m=briefkopf_gespeichert", status_code=303)


@router.get("/export", include_in_schema=False)
def export_data(request: Request, db: DB, user: CurrentUser):
    """DSGVO data export: everything the member owns, decrypted, as JSON."""
    patients = db.scalars(select(Patient).where(Patient.user_id == user.id)).all()
    letters = db.scalars(select(Letter).where(Letter.user_id == user.id).order_by(Letter.created_at)).all()
    generations = db.scalars(select(Generation).where(Generation.user_id == user.id)).all()
    subscription = db.scalar(select(Subscription).where(Subscription.user_id == user.id))

    payload = {
        "exported_at": utcnow().isoformat() + "Z",
        "format": "briefato-member-export/1",
        "account": {
            "email": user.email,
            "full_name": user.full_name,
            "practice_name": user.practice_name,
            "street": user.street,
            "zip": user.zip,
            "city": user.city,
            "country": user.country,
            "phone": user.phone,
            "tax_id": user.tax_id,
            "letterhead": user.letterhead_json or {},
            "created_at": _iso(user.created_at),
        },
        "patients": [
            {
                "id": patient.id,
                "external_ref": patient.external_ref,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "birth_date": _iso(patient.birth_date),
                "sex": patient.sex,
                "insurance": patient.insurance,
                "insurance_number": patient.insurance_number,
                "street": patient.street,
                "zip": patient.zip,
                "city": patient.city,
                "phone": patient.phone,
                "email": patient.email,
                "referring_doctor": patient.referring_doctor,
                "notes": decrypt_field(patient.notes_enc),
                "archived_at": _iso(patient.archived_at),
                "created_at": _iso(patient.created_at),
            }
            for patient in patients
        ],
        "letters": [
            {
                "id": letter.id,
                "patient_id": letter.patient_id,
                "kind": letter.kind,
                "status": letter.status,
                "title": letter.title,
                "dictation": decrypt_field(letter.dictation_enc),
                "content": decrypt_field(letter.content_enc),
                "created_at": _iso(letter.created_at),
                "approved_at": _iso(letter.approved_at),
            }
            for letter in letters
        ],
        "generations": [
            {
                "id": generation.id,
                "letter_id": generation.letter_id,
                "provider": generation.provider,
                "model": generation.model,
                "tokens_in": generation.tokens_in,
                "tokens_out": generation.tokens_out,
                "cost_usd": generation.cost_usd,
                "latency_ms": generation.latency_ms,
                "status": generation.status,
                "created_at": _iso(generation.created_at),
            }
            for generation in generations
        ],
        "subscription": (
            {
                "plan_code": subscription.plan_code,
                "status": subscription.status,
                "letters_quota": subscription.letters_quota,
                "letters_used": subscription.letters_used,
                "current_period_end": _iso(subscription.current_period_end),
            }
            if subscription
            else None
        ),
    }
    audit(db, event="account.exported", user_id=user.id, request=request)
    headers = {"Content-Disposition": 'attachment; filename="briefato-export.json"'}
    return JSONResponse(payload, headers=headers)


@router.post("/loeschen", include_in_schema=False, dependencies=[CSRF])
async def loeschen(request: Request, db: DB, user: CurrentUser):
    form = await request.form()
    if str(form.get("confirm", "")) != "ja":
        return RedirectResponse("/app/konto", status_code=303)
    user.is_active = False
    db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    db.commit()
    audit(db, event="account.deletion_requested", user_id=user.id, request=request)
    response = RedirectResponse("/?m=konto_loeschung", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response

"""Billing entry points. All money flows are delegated to the billing module (Stripe-hosted)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from .. import billing
from ..config import PLAN_CATALOG, get_settings
from ..security import audit
from .deps import CSRF, DB, CurrentUser, render
from .letters import _quota

logger = logging.getLogger("briefato.billing")

router = APIRouter(prefix="/app/abrechnung", tags=["abrechnung"])
webhook_router = APIRouter(tags=["webhooks"])


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
def abrechnung(request: Request, db: DB, user: CurrentUser, plan: str = "starter"):
    settings = get_settings()
    if plan not in PLAN_CATALOG or plan == "free":
        plan = "starter"
    try:
        url = billing.create_checkout_url(
            db,
            user,
            plan,
            success_url=f"{settings.base_url}/app/konto?m=billing_erfolg",
            cancel_url=f"{settings.base_url}/app/abrechnung?m=billing_abgebrochen",
        )
    except NotImplementedError:
        audit(db, event="billing.unavailable", user_id=user.id, request=request, plan=plan)
        return render(
            request,
            "app/billing/unavailable.html",
            error=None,
            quota=_quota(db, user),
            active="abrechnung",
            crumbs=[("Übersicht", "/app"), ("Abrechnung", None)],
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("checkout creation failed")
        return render(
            request,
            "app/billing/unavailable.html",
            error="Die Zahlungsanbindung hat einen Fehler gemeldet. Bitte versuchen Sie es später erneut.",
            quota=_quota(db, user),
            active="abrechnung",
            crumbs=[("Übersicht", "/app"), ("Abrechnung", None)],
        )
    if not url:
        return render(
            request,
            "app/billing/unavailable.html",
            error=None,
            quota=_quota(db, user),
            active="abrechnung",
            crumbs=[("Übersicht", "/app"), ("Abrechnung", None)],
        )
    return RedirectResponse(url, status_code=303)


@router.post("/portal", include_in_schema=False, dependencies=[CSRF])
def portal(request: Request, db: DB, user: CurrentUser):
    settings = get_settings()
    try:
        url = billing.create_portal_url(db, user, return_url=f"{settings.base_url}/app/konto")
    except NotImplementedError:
        audit(db, event="billing.unavailable", user_id=user.id, request=request)
        return render(
            request,
            "app/billing/unavailable.html",
            error=None,
            quota=_quota(db, user),
            active="abrechnung",
            crumbs=[("Übersicht", "/app"), ("Abrechnung", None)],
        )
    if not url:
        return RedirectResponse("/app/abrechnung", status_code=303)
    return RedirectResponse(url, status_code=303)


@webhook_router.post("/webhooks/stripe", include_in_schema=False)
async def stripe_webhook(request: Request, db: DB):
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        result = billing.handle_webhook(db, payload, signature)
    except NotImplementedError:
        logger.warning("stripe webhook received but billing module is not implemented")
        return JSONResponse({"handled": False, "event": "unavailable"}, status_code=503)
    except Exception as exc:  # noqa: BLE001 - never leak details to the caller
        logger.exception("stripe webhook failed")
        return JSONResponse({"handled": False, "event": "error"}, status_code=400)
    if not isinstance(result, dict):
        result = {"handled": bool(result), "event": ""}
    return JSONResponse(result)

"""Billing (Stripe-hosted flows only).

OWNER: WORKSTREAM-BILLING. This package file is a STUB so the portal can import the frozen
interface before the real implementation lands — replace it entirely.

Frozen signatures (docs/02-spec-interfaces.md §6):
    create_checkout_url(db, user, plan_code, success_url, cancel_url) -> str
    create_portal_url(db, user, return_url) -> str
    handle_webhook(db, payload: bytes, sig_header: str) -> dict
    quota_state(db, user) -> dict
"""

from __future__ import annotations

STUB = True


def create_checkout_url(db, user, plan_code: str, success_url: str, cancel_url: str) -> str:  # pragma: no cover
    raise NotImplementedError("billing stub: WORKSTREAM-BILLING has not landed yet")


def create_portal_url(db, user, return_url: str) -> str:  # pragma: no cover
    raise NotImplementedError("billing stub: WORKSTREAM-BILLING has not landed yet")


def handle_webhook(db, payload: bytes, sig_header: str) -> dict:  # pragma: no cover
    raise NotImplementedError("billing stub: WORKSTREAM-BILLING has not landed yet")


def quota_state(db, user) -> dict:  # pragma: no cover
    sub = getattr(user, "subscription", None)
    from ..config import PLAN_CATALOG, get_settings

    settings = get_settings()
    plan = getattr(sub, "plan_code", "free") or "free"
    quota = getattr(sub, "letters_quota", None) or PLAN_CATALOG.get(plan, {}).get(
        "letters", settings.quota_default_letters
    )
    used = getattr(sub, "letters_used", 0) or 0
    return {
        "plan": plan,
        "quota": int(quota),
        "used": int(used),
        "remaining": max(int(quota) - int(used), 0),
        "period_end": None,
    }

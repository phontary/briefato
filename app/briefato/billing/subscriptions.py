"""Subscription row helpers + the read-only quota projection.

OWNER: WORKSTREAM-BILLING.

The letter counter (``Subscription.letters_used``) is incremented **by the pipeline** on a
successful generation (app/briefato/pipeline/generate.py, WORKSTREAM-PIPELINE). This module
never consumes letters and never increments the counter; :func:`quota_state` only reads.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import PLAN_CATALOG, get_settings
from ..models import Subscription, User
from .plans import normalize_plan, plan_quota


def get_subscription(db: Session, user: User) -> Subscription | None:
    """Return the user's Subscription row without creating one (lazy-safe)."""
    if user is None or getattr(user, "id", None) is None:
        return None
    return db.scalar(select(Subscription).where(Subscription.user_id == user.id))


def find_by_customer_id(db: Session, stripe_customer_id: str | None) -> Subscription | None:
    if not stripe_customer_id:
        return None
    return db.scalar(
        select(Subscription).where(Subscription.stripe_customer_id == stripe_customer_id)
    )


def ensure_subscription(db: Session, user: User, plan_code: str = "free") -> Subscription:
    """Create the user's Subscription row lazily; safe to call twice (idempotent).

    Used at registration and before any Stripe interaction. Validates ``plan_code`` so an
    unknown plan raises a clear :class:`PlanError` instead of writing a broken row.
    """
    code = normalize_plan(plan_code)
    existing = get_subscription(db, user)
    if existing is not None:
        return existing
    sub = Subscription(
        user_id=user.id,
        plan_code=code,
        status="active",
        letters_quota=plan_quota(code),
        letters_used=0,
        cancel_at_period_end=False,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def apply_plan(sub: Subscription, plan_code: str | None) -> None:
    """Set plan_code + letters_quota from the catalogue (no commit)."""
    code = normalize_plan(plan_code or sub.plan_code)
    sub.plan_code = code
    sub.letters_quota = plan_quota(code)


def quota_state(db: Session, user: User) -> dict:
    """Read-only quota projection: ``{plan, quota, used, remaining, period_end, status}``.

    Never creates or mutates rows. Falls back to the free plan when the user has no
    Subscription row yet.
    """
    settings = get_settings()
    sub = get_subscription(db, user)

    plan = (getattr(sub, "plan_code", None) or "free") if sub is not None else "free"
    if plan not in PLAN_CATALOG:
        plan = "free"

    quota = None
    used = 0
    period_end = None
    status = "active"
    if sub is not None:
        quota = sub.letters_quota
        used = sub.letters_used or 0
        status = sub.status or "active"
        if sub.current_period_end is not None:
            period_end = sub.current_period_end.isoformat()

    if not quota:
        quota = PLAN_CATALOG.get(plan, {}).get("letters", settings.quota_default_letters)

    quota = int(quota)
    used = int(used)
    return {
        "plan": plan,
        "quota": quota,
        "used": used,
        "remaining": max(quota - used, 0),
        "period_end": period_end,
        "status": status,
    }


__all__ = [
    "apply_plan",
    "ensure_subscription",
    "find_by_customer_id",
    "get_subscription",
    "quota_state",
]

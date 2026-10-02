"""Stripe webhook intake — signature-verified, idempotent, mapping onto ``Subscription``.

OWNER: WORKSTREAM-BILLING.

Idempotency contract (docs/02-spec-interfaces.md §6):

* Every successfully applied Stripe event id is recorded as exactly **one** ``audit_events``
  row with ``event='stripe.webhook'`` and ``target_id=<stripe event id>``.
* If such a row already exists, the event is a replay: return
  ``{"handled": False, "event": <id>, "reason": "duplicate"}`` and change nothing.
* Unknown event types return ``{"handled": False, "event": <id>, "reason": "ignored"}`` and
  change nothing.
* A missing/invalid signature returns ``{"handled": False, "event": "", "reason":
  "invalid_signature"}`` and changes nothing.

No network calls beyond Stripe's own signature verification (which is pure crypto).
"""

from __future__ import annotations

from datetime import datetime, timezone

import stripe
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..models import AuditEvent, Subscription
from ..security import audit
from .errors import ConfigurationError
from .plans import plan_code_for_price_id, plan_quota
from .subscriptions import find_by_customer_id

#: Event types we actively map onto the Subscription row.
KNOWN_EVENTS: frozenset[str] = frozenset(
    {
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.paid",
        "invoice.payment_failed",
    }
)

#: Stripe subscription status -> our frozen status vocabulary (active|past_due|canceled).
STATUS_MAP: dict[str, str] = {
    "active": "active",
    "trialing": "active",
    "past_due": "past_due",
    "unpaid": "past_due",
    "incomplete": "past_due",
    "paused": "past_due",
    "incomplete_expired": "canceled",
    "canceled": "canceled",
}


# --------------------------------------------------------------------------- public API


def handle_webhook(db: Session, payload: bytes, sig_header: str) -> dict:
    settings = get_settings()
    if not (settings.stripe_webhook_secret or "").strip():
        raise ConfigurationError(
            "Stripe-Webhook ist nicht konfiguriert (BRIEFATO_STRIPE_WEBHOOK_SECRET fehlt). "
            "Bitte den Betreiber kontaktieren."
        )

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.SignatureVerificationError):
        return {"handled": False, "event": "", "reason": "invalid_signature"}

    event_id = str(_get(event, "id") or "")
    event_type = str(_get(event, "type") or "")
    if not event_id:
        return {"handled": False, "event": "", "reason": "invalid_signature"}

    # --- idempotency: one audit row per applied Stripe event id -------------------
    if _already_processed(db, event_id):
        return {"handled": False, "event": event_id, "reason": "duplicate"}

    if event_type not in KNOWN_EVENTS:
        return {"handled": False, "event": event_id, "reason": "ignored"}

    obj = _get(_get(event, "data", None), "object", None)
    changes = _apply(db, event_type, obj, settings)

    # Exactly one audit row per handled event — this row is also the idempotency marker.
    audit(
        db,
        event="stripe.webhook",
        user_id=changes.get("user_id"),
        target_type="stripe_event",
        target_id=event_id,
        stripe_event_type=event_type,
        changes={k: v for k, v in changes.items() if k not in ("user_id", "subscription_id")},
    )
    return {"handled": True, "event": event_id}


# --------------------------------------------------------------------------- handlers


def _apply(db: Session, event_type: str, obj, settings: Settings) -> dict:
    if event_type == "checkout.session.completed":
        return _checkout_completed(db, obj, settings)
    if event_type in ("customer.subscription.created", "customer.subscription.updated"):
        return _subscription_updated(db, obj, settings)
    if event_type == "customer.subscription.deleted":
        return _subscription_deleted(db, obj, settings)
    if event_type == "invoice.paid":
        return _invoice_paid(db, obj, settings)
    if event_type == "invoice.payment_failed":
        return _invoice_failed(db, obj, settings)
    return {}  # unreachable: caller filters on KNOWN_EVENTS


def _checkout_completed(db: Session, obj, settings: Settings) -> dict:
    sub, user_id = _resolve(db, obj, prefer_metadata=True)
    if sub is None:
        return {"user_id": user_id, "note": "no subscription row"}

    changes: dict = {"user_id": user_id, "subscription_id": sub.id}
    plan = _get(_get(obj, "metadata", None), "plan_code", None) or _get(
        _get(obj, "metadata", None), "plan", None
    )
    plan = _apply_plan(sub, plan)
    if plan:
        changes["plan_code"] = plan
        changes["letters_quota"] = sub.letters_quota

    if sub.status != "active":
        sub.status = "active"
    changes["status"] = sub.status

    subscription_id = _get(obj, "subscription") or _get(obj, "id")
    if _get(obj, "subscription"):
        sub.stripe_subscription_id = _get(obj, "subscription")
        changes["stripe_subscription_id"] = sub.stripe_subscription_id

    customer_id = _get(obj, "customer")
    if customer_id and not sub.stripe_customer_id:
        sub.stripe_customer_id = customer_id
        changes["stripe_customer_id"] = customer_id

    db.commit()
    return changes


def _subscription_updated(db: Session, obj, settings: Settings) -> dict:
    sub, user_id = _resolve(db, obj, prefer_metadata=True)
    if sub is None:
        return {"user_id": user_id, "note": "no subscription row"}

    changes: dict = {"user_id": user_id, "subscription_id": sub.id}

    stripe_id = _get(obj, "id")
    if stripe_id and sub.stripe_subscription_id != stripe_id:
        sub.stripe_subscription_id = stripe_id
        changes["stripe_subscription_id"] = stripe_id

    customer_id = _get(obj, "customer")
    if customer_id and sub.stripe_customer_id != customer_id:
        sub.stripe_customer_id = customer_id
        changes["stripe_customer_id"] = customer_id

    plan = _plan_from_subscription(obj, settings)
    if plan:
        _apply_plan(sub, plan)
        changes["plan_code"] = sub.plan_code
        changes["letters_quota"] = sub.letters_quota

    new_status = STATUS_MAP.get(str(_get(obj, "status") or ""), "past_due")
    if sub.status != new_status:
        sub.status = new_status
    changes["status"] = sub.status

    if _apply_period(sub, obj):
        changes["current_period_start"] = _iso(sub.current_period_start)
        changes["current_period_end"] = _iso(sub.current_period_end)

    cpe = bool(_get(obj, "cancel_at_period_end", False))
    if sub.cancel_at_period_end != cpe:
        sub.cancel_at_period_end = cpe
    changes["cancel_at_period_end"] = sub.cancel_at_period_end

    db.commit()
    return changes


def _subscription_deleted(db: Session, obj, settings: Settings) -> dict:
    sub, user_id = _resolve(db, obj, prefer_metadata=True)
    if sub is None:
        return {"user_id": user_id, "note": "no subscription row"}

    changes: dict = {"user_id": user_id, "subscription_id": sub.id}

    stripe_id = _get(obj, "id")
    if stripe_id:
        sub.stripe_subscription_id = stripe_id
        changes["stripe_subscription_id"] = stripe_id

    # Subscription ended: access falls back to the free plan.
    _apply_plan(sub, "free")
    changes["plan_code"] = sub.plan_code
    changes["letters_quota"] = sub.letters_quota

    sub.status = "canceled"
    sub.cancel_at_period_end = True
    changes["status"] = sub.status
    changes["cancel_at_period_end"] = True

    if _apply_period(sub, obj):
        changes["current_period_start"] = _iso(sub.current_period_start)
        changes["current_period_end"] = _iso(sub.current_period_end)

    db.commit()
    return changes


def _invoice_paid(db: Session, obj, settings: Settings) -> dict:
    sub, user_id = _resolve(db, obj, prefer_metadata=False)
    if sub is None:
        return {"user_id": user_id, "note": "no subscription row"}

    changes: dict = {"user_id": user_id, "subscription_id": sub.id}

    subscription_id = _get(obj, "subscription")
    if subscription_id and sub.stripe_subscription_id != subscription_id:
        sub.stripe_subscription_id = subscription_id
        changes["stripe_subscription_id"] = subscription_id

    sub.status = "active"
    changes["status"] = sub.status

    period_end = _get(obj, "period_end")
    if period_end:
        sub.current_period_end = _utc_naive(period_end)
        changes["current_period_end"] = _iso(sub.current_period_end)

    db.commit()
    return changes


def _invoice_failed(db: Session, obj, settings: Settings) -> dict:
    sub, user_id = _resolve(db, obj, prefer_metadata=False)
    if sub is None:
        return {"user_id": user_id, "note": "no subscription row"}

    changes: dict = {"user_id": user_id, "subscription_id": sub.id}

    subscription_id = _get(obj, "subscription")
    if subscription_id and sub.stripe_subscription_id != subscription_id:
        sub.stripe_subscription_id = subscription_id
        changes["stripe_subscription_id"] = subscription_id

    sub.status = "past_due"
    changes["status"] = sub.status

    db.commit()
    return changes


# --------------------------------------------------------------------------- helpers


def _already_processed(db: Session, event_id: str) -> bool:
    stmt = select(AuditEvent.id).where(
        AuditEvent.event == "stripe.webhook", AuditEvent.target_id == event_id
    )
    return db.scalar(stmt) is not None


def _resolve(db: Session, obj, prefer_metadata: bool = True):
    """Find the Subscription row for a Stripe object; return ``(subscription|None, user_id)``."""
    if obj is None:
        return None, None
    metadata = _get(obj, "metadata", None) or {}
    user_id = (
        _get(obj, "client_reference_id")
        or _get(metadata, "user_id")
        or _get(metadata, "briefato_user_id")
    )
    customer_id = _get(obj, "customer")

    sub = find_by_customer_id(db, customer_id)
    if sub is None and user_id:
        sub = db.scalar(select(Subscription).where(Subscription.user_id == user_id))
    if sub is not None:
        return sub, (user_id or sub.user_id)
    return None, user_id


def _plan_from_subscription(obj, settings: Settings) -> str | None:
    metadata = _get(obj, "metadata", None) or {}
    plan = _get(metadata, "plan_code")
    if plan:
        return plan
    items = _get(obj, "items", None)
    data = _get(items, "data", None) if items is not None else None
    if data:
        first = data[0]
        price = _get(first, "price", None)
        price_id = _get(price, "id") if price is not None else None
        resolved = plan_code_for_price_id(price_id, settings)
        if resolved:
            return resolved
    return None


def _apply_plan(sub: Subscription, plan_code: str | None) -> str | None:
    """Set plan_code + quota from the catalogue; unknown plans are ignored (no crash)."""
    if not plan_code:
        return None
    code = str(plan_code).strip().lower()
    from ..config import PLAN_CATALOG

    if code not in PLAN_CATALOG:
        return None
    sub.plan_code = code
    sub.letters_quota = plan_quota(code)
    return code


def _apply_period(sub: Subscription, obj) -> bool:
    changed = False
    start = _get(obj, "current_period_start")
    end = _get(obj, "current_period_end")
    if start:
        sub.current_period_start = _utc_naive(start)
        changed = True
    if end:
        sub.current_period_end = _utc_naive(end)
        changed = True
    return changed


def _utc_naive(ts) -> datetime | None:
    """Stripe epoch seconds -> tz-naive UTC datetime (matches the frozen model)."""
    if not ts:
        return None
    if isinstance(ts, datetime):
        return ts.astimezone(timezone.utc).replace(tzinfo=None) if ts.tzinfo else ts
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError, OSError):
        return None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _get(obj, key: str, default=None):
    """Read a field from a dict or a stripe ``StripeObject`` (both support item access)."""
    if obj is None:
        return default
    try:
        value = obj[key]
    except (KeyError, TypeError, IndexError, AttributeError):
        value = getattr(obj, key, default)
    return default if value is None else value


__all__ = ["KNOWN_EVENTS", "STATUS_MAP", "handle_webhook"]

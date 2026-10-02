"""Billing — Stripe-hosted flows only (architecture decision D6).

OWNER: WORKSTREAM-BILLING.

Frozen API (docs/02-spec-interfaces.md §6)::

    create_checkout_url(db, user, plan_code, success_url, cancel_url) -> str
    create_portal_url(db, user, return_url) -> str
    handle_webhook(db, payload: bytes, sig_header: str) -> dict
    quota_state(db, user) -> dict

Plus the helper :func:`ensure_subscription` used lazily at registration.

No card data ever touches this process: Checkout and the Customer Portal are Stripe-hosted.
The letter counter is incremented by the pipeline (WORKSTREAM-PIPELINE) on a successful
generation; nothing in this package increments ``Subscription.letters_used``.
"""

from __future__ import annotations

from .errors import BillingError, ConfigurationError, PlanError
from .plans import (
    PLAN_CODES,
    is_paid_plan,
    normalize_plan,
    plan_code_for_price_id,
    plan_price_id,
    plan_quota,
)
from .stripe_service import create_checkout_url, create_portal_url, ensure_customer
from .subscriptions import (
    apply_plan,
    ensure_subscription,
    find_by_customer_id,
    get_subscription,
    quota_state,
)
from .webhooks import KNOWN_EVENTS, STATUS_MAP, handle_webhook

__all__ = [
    "BillingError",
    "ConfigurationError",
    "KNOWN_EVENTS",
    "PLAN_CODES",
    "PlanError",
    "STATUS_MAP",
    "apply_plan",
    "create_checkout_url",
    "create_portal_url",
    "ensure_customer",
    "ensure_subscription",
    "find_by_customer_id",
    "get_subscription",
    "handle_webhook",
    "is_paid_plan",
    "normalize_plan",
    "plan_code_for_price_id",
    "plan_price_id",
    "plan_quota",
    "quota_state",
]

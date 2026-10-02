"""Stripe client wiring: Customer, Checkout and Billing Portal sessions.

OWNER: WORKSTREAM-BILLING.

Stripe-hosted flows only (architecture decision D6): we never see card data and never build
our own billing UI. Every public function here raises :class:`ConfigurationError` with a
German-safe message when a required ``BRIEFATO_STRIPE_*`` setting is missing, instead of
letting Stripe fail with an obscure 401.
"""

from __future__ import annotations

import logging

import stripe
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..models import User
from ..security import audit
from .errors import ConfigurationError
from .plans import normalize_plan, plan_price_id
from .subscriptions import ensure_subscription, get_subscription

log = logging.getLogger("briefato.billing")


# --------------------------------------------------------------------------- configuration


def _configure(settings: Settings) -> Settings:
    """Point the stripe module at the configured API key. Raises when unset."""
    secret = (settings.stripe_secret_key or "").strip()
    if not secret:
        raise ConfigurationError(
            "Stripe ist nicht konfiguriert (BRIEFATO_STRIPE_SECRET_KEY fehlt). "
            "Bitte den Betreiber kontaktieren."
        )
    stripe.api_key = secret
    return settings


# --------------------------------------------------------------------------- customer


def ensure_customer(db: Session, user: User, settings: Settings | None = None) -> str:
    """Return a Stripe customer id for the user, creating (and storing) it once.

    Reuses ``Subscription.stripe_customer_id`` when present. Customer creation uses a
    deterministic idempotency key derived from the user id, so concurrent checkout clicks
    cannot create duplicate customers.
    """
    settings = _configure(settings or get_settings())
    sub = ensure_subscription(db, user)
    if sub.stripe_customer_id:
        return sub.stripe_customer_id

    params: dict = {
        "email": user.email,
        "metadata": {"user_id": user.id},
        "idempotency_key": f"briefato-customer-{user.id}",
    }
    name = (user.practice_name or user.full_name or "").strip()
    if name:
        params["name"] = name

    customer = stripe.Customer.create(**params)
    customer_id = _attr(customer, "id")
    if not customer_id:
        raise ConfigurationError(
            "Stripe hat keine Kunden-ID zurückgegeben. Bitte den Betreiber kontaktieren."
        )
    sub.stripe_customer_id = customer_id
    db.commit()
    audit(
        db,
        event="billing.customer.created",
        user_id=user.id,
        target_type="subscription",
        target_id=sub.id,
        stripe_customer_id=customer_id,
    )
    return customer_id


# --------------------------------------------------------------------------- checkout


def create_checkout_url(
    db: Session,
    user: User,
    plan_code: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a subscription-mode Checkout Session and return its hosted URL."""
    settings = _configure(get_settings())
    code = normalize_plan(plan_code)
    price_id = plan_price_id(code, settings)
    customer_id = ensure_customer(db, user, settings=settings)

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=user.id,
        metadata={"user_id": user.id, "plan_code": code},
        subscription_data={"metadata": {"user_id": user.id, "plan_code": code}},
        allow_promotion_codes=True,
        idempotency_key=f"briefato-checkout-{user.id}-{code}",
    )
    url = _attr(session, "url")
    if not url:
        raise ConfigurationError(
            "Stripe hat keine Checkout-URL zurückgegeben. Bitte den Betreiber kontaktieren."
        )
    return url


# --------------------------------------------------------------------------- billing portal


def create_portal_url(db: Session, user: User, return_url: str) -> str:
    """Create a Stripe Billing Portal session for the user's stored customer."""
    _configure(get_settings())
    sub = get_subscription(db, user)
    customer_id = (getattr(sub, "stripe_customer_id", "") or "").strip() if sub else ""
    if not customer_id:
        raise ConfigurationError(
            "Es ist noch kein Stripe-Kundenkonto vorhanden. "
            "Bitte zuerst ein Abonnement abschließen."
        )
    session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    url = _attr(session, "url")
    if not url:
        raise ConfigurationError(
            "Stripe hat keine Portal-URL zurückgegeben. Bitte den Betreiber kontaktieren."
        )
    return url


# --------------------------------------------------------------------------- helpers


def _attr(obj, name: str, default=None):
    """Read a field from a dict or a stripe ``StripeObject`` (both support item access)."""
    if obj is None:
        return default
    try:
        value = obj[name]
    except (KeyError, TypeError, IndexError, AttributeError):
        value = getattr(obj, name, default)
    return default if value is None else value


__all__ = ["create_checkout_url", "create_portal_url", "ensure_customer"]

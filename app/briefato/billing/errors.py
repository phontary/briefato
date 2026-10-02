"""Billing error types.

OWNER: WORKSTREAM-BILLING.

Messages are deliberately operator-facing and German-safe: they must never contain secrets,
Stripe API keys or customer data. Callers (routes) can show them verbatim.
"""

from __future__ import annotations


class BillingError(RuntimeError):
    """Base class for every billing failure."""


class ConfigurationError(BillingError):
    """A required Stripe setting is missing or a Stripe call cannot be configured.

    Raised *before* any Stripe request is attempted so the failure mode is a clear German
    message instead of an obscure HTTP 401 from Stripe.
    """


class PlanError(BillingError, ValueError):
    """The requested plan code is unknown or has no configured Stripe price."""


__all__ = ["BillingError", "ConfigurationError", "PlanError"]

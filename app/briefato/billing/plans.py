"""Plan catalogue mapping: plan_code <-> Stripe price id + letter quota.

OWNER: WORKSTREAM-BILLING.

Single source of truth is ``config.PLAN_CATALOG`` (quotas) and the ``BRIEFATO_STRIPE_PRICE_*``
settings (prices). Nothing here performs network calls.
"""

from __future__ import annotations

from ..config import PLAN_CATALOG, Settings, get_settings
from .errors import ConfigurationError, PlanError

#: paid plans -> the settings attribute holding their Stripe price id.
PRICE_SETTING_BY_PLAN: dict[str, str] = {
    "starter": "stripe_price_starter",
    "praxis": "stripe_price_praxis",
    "klinik": "stripe_price_klinik",
}

PLAN_CODES: tuple[str, ...] = ("free", "starter", "praxis", "klinik")


def normalize_plan(plan_code: str | None) -> str:
    """Return a valid plan code or raise :class:`PlanError` (German-safe message)."""
    code = (plan_code or "").strip().lower()
    if code not in PLAN_CATALOG:
        raise PlanError(
            f"Unbekannter Tarif '{plan_code}'. Erlaubt sind: {', '.join(PLAN_CODES)}."
        )
    return code


def is_paid_plan(plan_code: str | None) -> bool:
    return (plan_code or "").strip().lower() in PRICE_SETTING_BY_PLAN


def plan_quota(plan_code: str | None, settings: Settings | None = None) -> int:
    """Letters included per billing period for a plan (from ``PLAN_CATALOG``)."""
    code = normalize_plan(plan_code)
    settings = settings or get_settings()
    entry = PLAN_CATALOG.get(code, {})
    return int(entry.get("letters", settings.quota_default_letters))


def plan_price_id(plan_code: str | None, settings: Settings | None = None) -> str:
    """Resolve a plan code to its configured Stripe price id.

    Raises :class:`PlanError` for an unknown plan or the free plan and
    :class:`ConfigurationError` when the price id has not been configured.
    """
    code = normalize_plan(plan_code)
    attr = PRICE_SETTING_BY_PLAN.get(code)
    if attr is None:
        raise PlanError(
            f"Der Tarif '{code}' ist kostenlos und hat keinen Stripe-Preis. "
            "Bitte einen bezahlten Tarif wählen."
        )
    settings = settings or get_settings()
    price_id = (getattr(settings, attr, "") or "").strip()
    if not price_id:
        raise ConfigurationError(
            f"Stripe-Preis für den Tarif '{code}' ist nicht konfiguriert "
            f"({attr.upper()} fehlt). Bitte den Betreiber kontaktieren."
        )
    return price_id


def plan_code_for_price_id(price_id: str | None, settings: Settings | None = None) -> str | None:
    """Reverse lookup price id -> plan code (``None`` when the price is unknown)."""
    if not price_id:
        return None
    settings = settings or get_settings()
    for code, attr in PRICE_SETTING_BY_PLAN.items():
        if (getattr(settings, attr, "") or "").strip() == price_id:
            return code
    return None


__all__ = [
    "PLAN_CODES",
    "PRICE_SETTING_BY_PLAN",
    "is_paid_plan",
    "normalize_plan",
    "plan_code_for_price_id",
    "plan_price_id",
    "plan_quota",
]

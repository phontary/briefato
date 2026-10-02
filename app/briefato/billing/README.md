# Briefato billing (WORKSTREAM-BILLING)

Stripe-hosted flows only (architecture decision D6): Checkout + Customer Portal + webhooks.
No card data touches the app; there is no billing UI of our own.

## Frozen API (docs/02-spec-interfaces.md §6)

```python
create_checkout_url(db, user, plan_code, success_url, cancel_url) -> str
create_portal_url(db, user, return_url) -> str
handle_webhook(db, payload: bytes, sig_header: str) -> dict   # idempotent
quota_state(db, user) -> dict
```

Extra helpers: `ensure_subscription(db, user, plan_code="free")` (lazy, idempotent),
`ensure_customer(db, user)`, plus `plans` / `subscriptions` / `webhooks` internals.
Errors: `ConfigurationError` (missing Stripe setting) and `PlanError` (unknown plan) —
both carry German-safe messages and never leak secrets.

## Layout

| File | Purpose |
|---|---|
| `plans.py` | plan_code -> Stripe price id (`BRIEFATO_STRIPE_PRICE_*`), quota from `PLAN_CATALOG` |
| `subscriptions.py` | Subscription row helpers, `ensure_subscription`, read-only `quota_state` |
| `stripe_service.py` | Customer / Checkout / Billing Portal session creation |
| `webhooks.py` | signature verify + idempotent event -> Subscription mapping |
| `errors.py` | `BillingError`, `ConfigurationError`, `PlanError` |
| `simulate_lifecycle.py` | offline end-to-end simulation (fake Stripe, no network) |

## Contracts

* `handle_webhook` is **idempotent**: one `audit_events` row per Stripe event id
  (`event='stripe.webhook'`, `target_id=<event id>`). A replay returns
  `{"handled": False, "event": ..., "reason": "duplicate"}` and changes nothing.
  Unknown types return `{"handled": False, "event": ..., "reason": "ignored"}`.
  A bad signature returns `{"handled": False, "event": "", "reason": "invalid_signature"}`.
* `quota_state` is **read-only** (never creates rows) and falls back to the free plan when no
  Subscription row exists. It returns `{plan, quota, used, remaining, period_end, status}`.
* The letter counter (`Subscription.letters_used`) is incremented by the **pipeline**
  (WORKSTREAM-PIPELINE) on a successful generation. Nothing in this package increments it.

## Self-check (fully offline)

```bash
# from the repo root
/workspace/briefato/.venv/bin/python -m pytest app/tests/test_billing.py -q
/workspace/briefato/.venv/bin/python app/briefato/billing/simulate_lifecycle.py
```

Both monkeypatch/fake the `stripe` module; no network, no real API keys required. The tests
set dummy `BRIEFATO_STRIPE_*` env vars and a temporary `BRIEFATO_DB_URL` before importing
`briefato` (config is `lru_cache`d and the DB engine is bound at import time).

## Configuration

`BRIEFATO_STRIPE_SECRET_KEY`, `BRIEFATO_STRIPE_WEBHOOK_SECRET`,
`BRIEFATO_STRIPE_PRICE_STARTER`, `BRIEFATO_STRIPE_PRICE_PRAXIS`,
`BRIEFATO_STRIPE_PRICE_KLINIK`. Missing values raise `ConfigurationError` before any Stripe
request is attempted. Price ids are still test placeholders — see the workstream report.

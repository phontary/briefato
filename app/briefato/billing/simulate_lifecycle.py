"""Offline billing lifecycle simulation — fake stripe, no network, no real keys.

Drives: checkout -> customer.subscription.updated webhook -> quota_state -> replay
(idempotency) -> invoice.payment_failed, then prints the resulting Subscription row and
every ``stripe.webhook`` audit row.

Run:
    /workspace/briefato/.venv/bin/python app/briefato/billing/simulate_lifecycle.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

TMP = tempfile.mkdtemp(prefix="briefato-billing-sim-")
os.environ["BRIEFATO_DATA_DIR"] = TMP
os.environ["BRIEFATO_DB_URL"] = f"sqlite:///{Path(TMP) / 'sim.db'}"
os.environ["BRIEFATO_SECRET_KEY"] = "sim-secret"
os.environ["BRIEFATO_LLM_MOCK"] = "true"
os.environ["BRIEFATO_STRIPE_SECRET_KEY"] = "sk_test_dummy"
os.environ["BRIEFATO_STRIPE_WEBHOOK_SECRET"] = "whsec_dummy"
os.environ["BRIEFATO_STRIPE_PRICE_STARTER"] = "price_starter_test"
os.environ["BRIEFATO_STRIPE_PRICE_PRAXIS"] = "price_praxis_test"
os.environ["BRIEFATO_STRIPE_PRICE_KLINIK"] = "price_klinik_test"

import stripe  # noqa: E402
from sqlalchemy import select  # noqa: E402

from briefato.billing import (  # noqa: E402
    create_checkout_url,
    handle_webhook,
    quota_state,
)
from briefato.db import SessionLocal, init_db  # noqa: E402
from briefato.models import AuditEvent, Subscription, User  # noqa: E402

EPOCH_START, EPOCH_END = 1761955200, 1764547200  # 2025-11-01 / 2025-12-01 UTC


def _dt(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).replace(tzinfo=None).isoformat()


def main() -> None:
    init_db()

    # --- fake stripe --------------------------------------------------------------------
    events: dict = {}
    stripe.Customer.create = lambda **kw: {"id": "cus_sim_001"}  # type: ignore[assignment]
    stripe.checkout.Session.create = (  # type: ignore[assignment]
        lambda **kw: {"id": "cs_sim_001", "url": "https://checkout.stripe.test/cs_sim_001"}
    )

    def _construct(payload, sig_header, secret, **kw):
        return events["current"]

    stripe.Webhook.construct_event = _construct  # type: ignore[assignment]

    db = SessionLocal()
    user = User(
        email=f"sim-{uuid.uuid4().hex[:8]}@praxis-sim.de",
        password_hash="x",
        practice_name="Simulationspraxis",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    print("== 1) checkout ==")
    url = create_checkout_url(
        db, user, "praxis", "https://app.briefato.test/app?ok=1", "https://app.briefato.test/preise"
    )
    sub = db.scalar(select(Subscription).where(Subscription.user_id == user.id))
    print(f"checkout url          : {url}")
    print(f"stored customer id    : {sub.stripe_customer_id}")

    print("\n== 2) customer.subscription.updated webhook ==")
    events["current"] = {
        "id": "evt_sim_upd_1",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_sim_001",
                "customer": sub.stripe_customer_id,
                "status": "active",
                "cancel_at_period_end": False,
                "current_period_start": EPOCH_START,
                "current_period_end": EPOCH_END,
                "metadata": {},
                "items": {"data": [{"price": {"id": "price_praxis_test"}}]},
            }
        },
    }
    print(f"result                : {handle_webhook(db, b'{}', 't=1,v1=x')}")

    print("\n== 3) quota_state ==")
    print(f"quota_state           : {quota_state(db, user)}")

    print("\n== 4) replay same event (idempotency) ==")
    print(f"result                : {handle_webhook(db, b'{}', 't=1,v1=x')}")

    print("\n== 5) invoice.payment_failed webhook ==")
    events["current"] = {
        "id": "evt_sim_fail_1",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": "in_sim_1",
                "customer": sub.stripe_customer_id,
                "subscription": "sub_sim_001",
            }
        },
    }
    print(f"result                : {handle_webhook(db, b'{}', 't=1,v1=x')}")

    db.refresh(sub)
    print("\n== Subscription row ==")
    print(f"plan_code             : {sub.plan_code}")
    print(f"status                : {sub.status}")
    print(f"stripe_customer_id    : {sub.stripe_customer_id}")
    print(f"stripe_subscription_id: {sub.stripe_subscription_id}")
    print(f"current_period_start  : {sub.current_period_start.isoformat() if sub.current_period_start else None}")
    print(f"current_period_end    : {sub.current_period_end.isoformat() if sub.current_period_end else None}")
    print(f"letters_quota / used  : {sub.letters_quota} / {sub.letters_used}")
    print(f"cancel_at_period_end  : {sub.cancel_at_period_end}")

    print("\n== stripe.webhook audit rows ==")
    rows = db.scalars(
        select(AuditEvent).where(AuditEvent.event == "stripe.webhook").order_by(AuditEvent.created_at)
    ).all()
    for row in rows:
        print(f"  {row.target_id:16} type={row.meta_json.get('stripe_event_type'):30} changes={row.meta_json.get('changes')}")
    print(f"  total stripe.webhook rows: {len(rows)}")

    db.close()


if __name__ == "__main__":
    main()

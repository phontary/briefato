"""Offline tests for the Stripe billing module (WORKSTREAM-BILLING).

Fully offline: the ``stripe`` module's network entry points are monkeypatched; no real API
key and no network access are required.

Run:
    /workspace/briefato/.venv/bin/python -m pytest app/tests/test_billing.py -q
"""

from __future__ import annotations

import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

# --- environment must be set BEFORE importing briefato (config is lru_cached, db engine bound) ---
TMP = tempfile.mkdtemp(prefix="briefato-billing-test-")
os.environ["BRIEFATO_DATA_DIR"] = TMP
os.environ["BRIEFATO_DB_URL"] = f"sqlite:///{Path(TMP) / 'billing.db'}"
os.environ["BRIEFATO_LLM_MOCK"] = "true"
os.environ["BRIEFATO_SECRET_KEY"] = "test-secret"
os.environ["BRIEFATO_STRIPE_SECRET_KEY"] = "sk_test_dummy"
os.environ["BRIEFATO_STRIPE_WEBHOOK_SECRET"] = "whsec_dummy"
os.environ["BRIEFATO_STRIPE_PRICE_STARTER"] = "price_starter_test"
os.environ["BRIEFATO_STRIPE_PRICE_PRAXIS"] = "price_praxis_test"
os.environ["BRIEFATO_STRIPE_PRICE_KLINIK"] = "price_klinik_test"

import pytest  # noqa: E402
import stripe  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from briefato import billing  # noqa: E402
from briefato.billing import (  # noqa: E402
    ConfigurationError,
    PlanError,
    create_checkout_url,
    create_portal_url,
    ensure_subscription,
    handle_webhook,
    quota_state,
)
from briefato.config import get_settings  # noqa: E402
from briefato.db import SessionLocal, init_db  # noqa: E402
from briefato.models import AuditEvent, Subscription, User  # noqa: E402


# --------------------------------------------------------------------------- fixtures


@pytest.fixture(scope="module", autouse=True)
def _db():
    init_db()
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def user(db):
    u = User(
        email=f"arzt-{uuid.uuid4().hex[:10]}@praxis-test.de",
        password_hash="x",
        full_name="Dr. med. Test",
        practice_name="Praxis Test",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# --------------------------------------------------------------------------- fakes


class _Recorder:
    def __init__(self):
        self.calls = []

    def make(self, result):
        def _call(**kwargs):
            self.calls.append(kwargs)
            return result

        return _call


def _patch_construct_event(monkeypatch, event):
    def _construct(payload, sig_header, secret, **kwargs):
        return event

    monkeypatch.setattr(stripe.Webhook, "construct_event", _construct)


def _patch_construct_event_raising(monkeypatch):
    def _construct(payload, sig_header, secret, **kwargs):
        raise stripe.SignatureVerificationError("bad signature", sig_header or "")

    monkeypatch.setattr(stripe.Webhook, "construct_event", _construct)


EPOCH_START = 1761955200  # 2025-11-01T00:00:00Z
EPOCH_END = 1764547200  # 2025-12-01T00:00:00Z


def _expected_dt(epoch: int) -> datetime:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).replace(tzinfo=None)


def _cust(user) -> str:
    """A per-user unique fake Stripe customer id (real ids are unique per customer)."""
    return f"cus_{user.id}"


def _subscription_event(
    event_id: str,
    event_type: str,
    *,
    customer: str | None = None,
    status: str = "active",
    price_id: str | None = "price_praxis_test",
    period_start: int | None = EPOCH_START,
    period_end: int | None = EPOCH_END,
    cancel_at_period_end: bool = False,
    metadata: dict | None = None,
) -> dict:
    obj: dict = {
        "id": "sub_test_001",
        "customer": customer,
        "status": status,
        "cancel_at_period_end": cancel_at_period_end,
        "metadata": metadata or {},
        "items": {"data": ([{"price": {"id": price_id}}] if price_id else [])},
    }
    if period_start is not None:
        obj["current_period_start"] = period_start
    if period_end is not None:
        obj["current_period_end"] = period_end
    return {"id": event_id, "type": event_type, "data": {"object": obj}}


def _stripe_webhook_audits(db) -> list[AuditEvent]:
    return list(
        db.scalars(select(AuditEvent).where(AuditEvent.event == "stripe.webhook")).all()
    )


# --------------------------------------------------------------------------- plans


def test_plan_quota_matches_catalog():
    assert billing.plan_quota("free") == 10
    assert billing.plan_quota("starter") == 40
    assert billing.plan_quota("praxis") == 120
    assert billing.plan_quota("klinik") == 400


def test_unknown_plan_raises_clear_error():
    with pytest.raises(PlanError):
        billing.plan_quota("gold")
    with pytest.raises(PlanError):
        billing.plan_price_id("gold")
    # free plan has no Stripe price
    with pytest.raises(PlanError):
        billing.plan_price_id("free")


def test_price_resolution_from_settings():
    settings = get_settings()
    assert billing.plan_price_id("praxis", settings) == "price_praxis_test"
    assert billing.plan_code_for_price_id("price_starter_test", settings) == "starter"
    assert billing.plan_code_for_price_id("price_unknown", settings) is None


# --------------------------------------------------------------------------- checkout


def test_checkout_session_creation(monkeypatch, db, user):
    customer_rec = _Recorder()
    checkout_rec = _Recorder()
    monkeypatch.setattr(
        stripe.Customer, "create", customer_rec.make({"id": "cus_test_001"})
    )
    monkeypatch.setattr(
        stripe.checkout.Session,
        "create",
        checkout_rec.make(
            {"id": "cs_test_001", "url": "https://checkout.stripe.test/cs_test_001"}
        ),
    )

    url = create_checkout_url(
        db,
        user,
        "praxis",
        success_url="https://app.briefato.test/app?ok=1",
        cancel_url="https://app.briefato.test/preise",
    )

    assert url == "https://checkout.stripe.test/cs_test_001"
    assert len(customer_rec.calls) == 1
    assert len(checkout_rec.calls) == 1

    params = checkout_rec.calls[0]
    assert params["mode"] == "subscription"
    assert params["client_reference_id"] == user.id
    assert params["metadata"] == {"user_id": user.id, "plan_code": "praxis"}
    assert params["subscription_data"]["metadata"]["user_id"] == user.id
    assert params["subscription_data"]["metadata"]["plan_code"] == "praxis"
    assert params["line_items"] == [{"price": "price_praxis_test", "quantity": 1}]
    assert params["customer"] == "cus_test_001"
    assert params["success_url"] == "https://app.briefato.test/app?ok=1"
    assert params["cancel_url"] == "https://app.briefato.test/preise"

    # customer id is persisted on the Subscription row
    sub = db.scalar(select(Subscription).where(Subscription.user_id == user.id))
    assert sub is not None and sub.stripe_customer_id == "cus_test_001"


def test_checkout_reuses_stored_customer(monkeypatch, db, user):
    customer_rec = _Recorder()
    checkout_rec = _Recorder()
    monkeypatch.setattr(stripe.Customer, "create", customer_rec.make({"id": "cus_reuse"}))
    monkeypatch.setattr(
        stripe.checkout.Session,
        "create",
        checkout_rec.make({"url": "https://checkout.stripe.test/x"}),
    )

    create_checkout_url(db, user, "starter", "https://s", "https://c")
    create_checkout_url(db, user, "praxis", "https://s", "https://c")

    assert len(customer_rec.calls) == 1  # second call reused the stored customer
    assert len(checkout_rec.calls) == 2
    assert checkout_rec.calls[0]["customer"] == "cus_reuse"
    assert checkout_rec.calls[1]["customer"] == "cus_reuse"


def test_checkout_unknown_plan_raises(monkeypatch, db, user):
    with pytest.raises(PlanError):
        create_checkout_url(db, user, "gold", "https://s", "https://c")


# --------------------------------------------------------------------------- portal


def test_portal_url_uses_stored_customer(monkeypatch, db, user):
    sub = ensure_subscription(db, user)
    sub.stripe_customer_id = "cus_test_002"
    db.commit()

    rec = _Recorder()
    monkeypatch.setattr(
        stripe.billing_portal.Session,
        "create",
        rec.make({"url": "https://billing.stripe.test/p/session"}),
    )

    url = create_portal_url(db, user, return_url="https://app.briefato.test/app/konto")
    assert url == "https://billing.stripe.test/p/session"
    assert rec.calls[0]["customer"] == "cus_test_002"
    assert rec.calls[0]["return_url"] == "https://app.briefato.test/app/konto"


def test_portal_without_customer_raises(monkeypatch, db, user):
    with pytest.raises(ConfigurationError):
        create_portal_url(db, user, return_url="https://app.briefato.test/app/konto")


# --------------------------------------------------------------------------- configuration errors


def test_missing_secret_key_raises_clear_error(monkeypatch, db, user):
    monkeypatch.setattr(get_settings(), "stripe_secret_key", "")
    with pytest.raises(ConfigurationError):
        create_checkout_url(db, user, "praxis", "https://s", "https://c")


def test_missing_price_id_raises_clear_error(monkeypatch, db, user):
    monkeypatch.setattr(get_settings(), "stripe_price_praxis", "")
    with pytest.raises(ConfigurationError):
        create_checkout_url(db, user, "praxis", "https://s", "https://c")


def test_webhook_missing_secret_raises(monkeypatch, db):
    monkeypatch.setattr(get_settings(), "stripe_webhook_secret", "")
    with pytest.raises(ConfigurationError):
        handle_webhook(db, b"{}", "t=1,v1=x")


# --------------------------------------------------------------------------- webhooks


def test_webhook_bad_signature_changes_nothing(monkeypatch, db, user):
    sub = ensure_subscription(db, user)
    sub.stripe_customer_id = _cust(user)
    db.commit()
    before = (sub.plan_code, sub.status, sub.letters_quota)
    audit_before = len(_stripe_webhook_audits(db))

    _patch_construct_event_raising(monkeypatch)
    result = handle_webhook(db, b'{"bad": true}', "t=1,v1=deadbeef")

    assert result == {"handled": False, "event": "", "reason": "invalid_signature"}
    db.refresh(sub)
    assert (sub.plan_code, sub.status, sub.letters_quota) == before
    assert len(_stripe_webhook_audits(db)) == audit_before


def test_webhook_subscription_updated_maps_row_and_writes_one_audit(monkeypatch, db, user):
    sub = ensure_subscription(db, user)
    sub.stripe_customer_id = _cust(user)
    db.commit()
    audit_before = len(_stripe_webhook_audits(db))

    event = _subscription_event(
        "evt_upd_1",
        "customer.subscription.updated",
        customer=_cust(user),
        status="active",
        price_id="price_praxis_test",
        cancel_at_period_end=True,
    )
    _patch_construct_event(monkeypatch, event)

    result = handle_webhook(db, b"{}", "t=1,v1=x")
    assert result == {"handled": True, "event": "evt_upd_1"}

    db.refresh(sub)
    assert sub.plan_code == "praxis"
    assert sub.letters_quota == 120
    assert sub.status == "active"
    assert sub.stripe_subscription_id == "sub_test_001"
    assert sub.current_period_start == _expected_dt(EPOCH_START)
    assert sub.current_period_end == _expected_dt(EPOCH_END)
    assert sub.current_period_end.tzinfo is None  # tz-naive UTC
    assert sub.cancel_at_period_end is True

    audits = _stripe_webhook_audits(db)
    assert len(audits) == audit_before + 1
    newest = audits[-1]
    assert newest.target_id == "evt_upd_1"
    assert newest.target_type == "stripe_event"
    assert newest.user_id == user.id


def test_webhook_replay_is_idempotent(monkeypatch, db, user):
    sub = ensure_subscription(db, user)
    sub.stripe_customer_id = _cust(user)
    db.commit()

    event = _subscription_event("evt_dup_1", "customer.subscription.updated", customer=_cust(user))
    _patch_construct_event(monkeypatch, event)

    first = handle_webhook(db, b"{}", "t=1,v1=x")
    assert first == {"handled": True, "event": "evt_dup_1"}
    db.refresh(sub)
    snapshot = (
        sub.plan_code,
        sub.status,
        sub.letters_quota,
        sub.stripe_subscription_id,
        sub.current_period_start,
        sub.current_period_end,
    )
    audits_after_first = len(_stripe_webhook_audits(db))

    second = handle_webhook(db, b"{}", "t=1,v1=x")
    assert second == {"handled": False, "event": "evt_dup_1", "reason": "duplicate"}

    db.refresh(sub)
    assert (
        sub.plan_code,
        sub.status,
        sub.letters_quota,
        sub.stripe_subscription_id,
        sub.current_period_start,
        sub.current_period_end,
    ) == snapshot
    assert len(_stripe_webhook_audits(db)) == audits_after_first  # no second audit row


def test_webhook_unknown_event_ignored(monkeypatch, db, user):
    sub = ensure_subscription(db, user)
    sub.stripe_customer_id = _cust(user)
    db.commit()
    audit_before = len(_stripe_webhook_audits(db))

    event = {"id": "evt_unknown_1", "type": "customer.created", "data": {"object": {}}}
    _patch_construct_event(monkeypatch, event)

    result = handle_webhook(db, b"{}", "t=1,v1=x")
    assert result == {"handled": False, "event": "evt_unknown_1", "reason": "ignored"}
    db.refresh(sub)
    assert sub.plan_code == "free"
    assert len(_stripe_webhook_audits(db)) == audit_before


def test_webhook_checkout_completed_activates_plan(monkeypatch, db, user):
    sub = ensure_subscription(db, user)
    db.commit()

    event = {
        "id": "evt_checkout_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_001",
                "customer": "cus_checkout",
                "subscription": "sub_checkout_1",
                "client_reference_id": user.id,
                "metadata": {"user_id": user.id, "plan_code": "starter"},
            }
        },
    }
    _patch_construct_event(monkeypatch, event)

    result = handle_webhook(db, b"{}", "t=1,v1=x")
    assert result == {"handled": True, "event": "evt_checkout_1"}

    db.refresh(sub)
    assert sub.plan_code == "starter"
    assert sub.letters_quota == 40
    assert sub.status == "active"
    assert sub.stripe_subscription_id == "sub_checkout_1"
    assert sub.stripe_customer_id == "cus_checkout"


def test_webhook_subscription_deleted_downgrades(monkeypatch, db, user):
    sub = ensure_subscription(db, user, plan_code="praxis")
    sub.stripe_customer_id = _cust(user)
    sub.stripe_subscription_id = "sub_test_001"
    db.commit()

    event = _subscription_event(
        "evt_del_1",
        "customer.subscription.deleted",
        customer=_cust(user),
        status="canceled",
        price_id="price_praxis_test",
    )
    _patch_construct_event(monkeypatch, event)

    result = handle_webhook(db, b"{}", "t=1,v1=x")
    assert result == {"handled": True, "event": "evt_del_1"}

    db.refresh(sub)
    assert sub.status == "canceled"
    assert sub.plan_code == "free"
    assert sub.letters_quota == 10
    assert sub.cancel_at_period_end is True


def test_webhook_invoice_payment_failed_sets_past_due(monkeypatch, db, user):
    sub = ensure_subscription(db, user, plan_code="praxis")
    sub.stripe_customer_id = _cust(user)
    db.commit()

    event = {
        "id": "evt_inv_fail_1",
        "type": "invoice.payment_failed",
        "data": {"object": {"id": "in_1", "customer": _cust(user), "subscription": "sub_test_001"}},
    }
    _patch_construct_event(monkeypatch, event)

    assert handle_webhook(db, b"{}", "t=1,v1=x") == {"handled": True, "event": "evt_inv_fail_1"}
    db.refresh(sub)
    assert sub.status == "past_due"
    assert sub.stripe_subscription_id == "sub_test_001"


def test_webhook_invoice_paid_sets_active_and_period_end(monkeypatch, db, user):
    sub = ensure_subscription(db, user, plan_code="praxis")
    sub.stripe_customer_id = _cust(user)
    sub.status = "past_due"
    db.commit()

    event = {
        "id": "evt_inv_paid_1",
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "in_2",
                "customer": _cust(user),
                "subscription": "sub_test_001",
                "period_end": EPOCH_END,
            }
        },
    }
    _patch_construct_event(monkeypatch, event)

    assert handle_webhook(db, b"{}", "t=1,v1=x") == {"handled": True, "event": "evt_inv_paid_1"}
    db.refresh(sub)
    assert sub.status == "active"
    assert sub.current_period_end == _expected_dt(EPOCH_END)


def test_webhook_event_without_id_is_rejected(monkeypatch, db):
    _patch_construct_event(monkeypatch, {"type": "customer.subscription.updated", "data": {"object": {}}})
    result = handle_webhook(db, b"{}", "t=1,v1=x")
    assert result == {"handled": False, "event": "", "reason": "invalid_signature"}


# --------------------------------------------------------------------------- quota_state


def test_quota_state_free_without_subscription(db, user):
    state = quota_state(db, user)
    assert state["plan"] == "free"
    assert state["quota"] == 10
    assert state["used"] == 0
    assert state["remaining"] == 10
    assert state["period_end"] is None
    assert state["status"] == "active"
    # quota_state must not create a row
    assert db.scalar(select(Subscription).where(Subscription.user_id == user.id)) is None


def test_quota_state_paid_plan_math(db, user):
    sub = ensure_subscription(db, user, plan_code="praxis")
    sub.current_period_end = _expected_dt(EPOCH_END)
    sub.letters_used = 100
    db.commit()

    state = quota_state(db, user)
    assert state == {
        "plan": "praxis",
        "quota": 120,
        "used": 100,
        "remaining": 20,
        "period_end": _expected_dt(EPOCH_END).isoformat(),
        "status": "active",
    }


def test_quota_state_remaining_never_negative(db, user):
    sub = ensure_subscription(db, user, plan_code="starter")
    sub.letters_used = 50
    db.commit()

    state = quota_state(db, user)
    assert state["quota"] == 40
    assert state["used"] == 50
    assert state["remaining"] == 0


# --------------------------------------------------------------------------- ensure_subscription


def test_ensure_subscription_is_idempotent(db, user):
    first = ensure_subscription(db, user)
    second = ensure_subscription(db, user, plan_code="klinik")  # ignored: row exists

    assert first.id == second.id
    assert second.plan_code == "free"
    count = db.scalar(
        select(func.count()).select_from(Subscription).where(Subscription.user_id == user.id)
    )
    assert count == 1


def test_ensure_subscription_validates_plan(db, user):
    with pytest.raises(PlanError):
        ensure_subscription(db, user, plan_code="nope")

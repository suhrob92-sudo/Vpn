"""Referral rewards: inviter gets bonus days on invited user's FIRST payment only."""
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from app.core.db import get_session_factory
from app.core.time import aware_utc
from app.models import (
    Payment,
    PaymentStatus,
    Plan,
    ReferralEvent,
    Subscription,
    SubscriptionStatus,
    User,
)

CRYPTOBOT_TOKEN = "999:test-cryptobot-token"
WEBHOOK_PATH = "/payments/webhook/cryptobot/hooksecret"


def sign(body: bytes) -> str:
    secret = hashlib.sha256(CRYPTOBOT_TOKEN.encode()).digest()
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


def webhook_body(invoice_id: int) -> bytes:
    return json.dumps(
        {
            "update_id": 1,
            "update_type": "invoice_paid",
            "request_date": "2026-07-06T10:00:00Z",
            "payload": {"invoice_id": invoice_id, "status": "paid"},
        }
    ).encode()


async def seed() -> dict:
    """Inviter with an active 10-day subscription; invited user with a TRACKED
    referral event and two pending payments (first + renewal)."""
    now = datetime.now(timezone.utc)
    async with get_session_factory()() as db:
        plan = Plan(name="1 oylik", price=3, currency="USDT", duration_days=30)
        inviter = User(telegram_id=100, referral_code="inv100")
        db.add_all([plan, inviter])
        await db.flush()
        invited = User(telegram_id=200, referral_code="inv200", referred_by=inviter.id)
        db.add(invited)
        await db.flush()
        db.add(ReferralEvent(inviter_id=inviter.id, invited_user_id=invited.id))
        inviter_sub = Subscription(
            user_id=inviter.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE.value,
            started_at=now,
            expires_at=now + timedelta(days=10),
        )
        db.add(inviter_sub)
        for invoice in (71, 72):
            db.add(
                Payment(
                    user_id=invited.id,
                    plan_id=plan.id,
                    provider="cryptobot",
                    provider_payment_id=f"cryptobot:{invoice}",
                    amount=3,
                    currency="USDT",
                    status=PaymentStatus.PENDING.value,
                )
            )
        await db.commit()
        return {
            "inviter_id": inviter.id,
            "inviter_sub_id": inviter_sub.id,
            "expires": inviter_sub.expires_at,
        }


async def test_first_payment_rewards_inviter_once(client):
    ids = await seed()

    with patch("app.services.referral.send_message", new=AsyncMock(return_value=True)) as sent:
        for invoice in (71, 72):  # first payment + a renewal
            body = webhook_body(invoice)
            resp = await client.post(
                WEBHOOK_PATH,
                content=body,
                headers={
                    "crypto-pay-api-signature": sign(body),
                    "content-type": "application/json",
                },
            )
            assert resp.status_code == 200, resp.text

    async with get_session_factory()() as db:
        sub = await db.get(Subscription, ids["inviter_sub_id"])
        event = await db.scalar(select(ReferralEvent))
        # exactly one reward: +7 days, not +14
        assert aware_utc(sub.expires_at) == ids["expires"] + timedelta(days=7)
        assert event.status == "REWARDED"
    assert sent.await_count == 1


async def test_reward_pending_when_inviter_has_no_sub(client):
    async with get_session_factory()() as db:
        plan = Plan(name="1 oylik", price=3, currency="USDT", duration_days=30)
        inviter = User(telegram_id=300, referral_code="inv300")
        db.add_all([plan, inviter])
        await db.flush()
        invited = User(telegram_id=400, referral_code="inv400", referred_by=inviter.id)
        db.add(invited)
        await db.flush()
        db.add(ReferralEvent(inviter_id=inviter.id, invited_user_id=invited.id))
        db.add(
            Payment(
                user_id=invited.id,
                plan_id=plan.id,
                provider="cryptobot",
                provider_payment_id="cryptobot:81",
                amount=3,
                currency="USDT",
                status=PaymentStatus.PENDING.value,
            )
        )
        await db.commit()

    body = webhook_body(81)
    resp = await client.post(
        WEBHOOK_PATH,
        content=body,
        headers={"crypto-pay-api-signature": sign(body), "content-type": "application/json"},
    )
    assert resp.status_code == 200

    async with get_session_factory()() as db:
        event = await db.scalar(select(ReferralEvent))
        assert event.status == "REWARD_PENDING"

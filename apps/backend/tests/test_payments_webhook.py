"""CryptoBot webhook: signature verification + idempotent activation."""
import hashlib
import hmac
import json

from sqlalchemy import func, select

from app.core.db import get_session_factory
from app.models import Payment, PaymentStatus, Plan, Subscription, User

CRYPTOBOT_TOKEN = "999:test-cryptobot-token"
WEBHOOK_PATH = "/payments/webhook/cryptobot/hooksecret"


def sign(body: bytes) -> str:
    secret = hashlib.sha256(CRYPTOBOT_TOKEN.encode()).digest()
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


async def seed_pending_payment() -> int:
    async with get_session_factory()() as db:
        user = User(telegram_id=555, referral_code="ref555")
        plan = Plan(name="1 oylik", price=3, currency="USDT", duration_days=30)
        db.add_all([user, plan])
        await db.flush()
        payment = Payment(
            user_id=user.id,
            plan_id=plan.id,
            provider="cryptobot",
            provider_payment_id="cryptobot:42",
            amount=3,
            currency="USDT",
            status=PaymentStatus.PENDING.value,
        )
        db.add(payment)
        await db.commit()
        return payment.id


def webhook_body(invoice_id: int = 42, internal_payment_id: int | None = None) -> bytes:
    update = {
        "update_id": 1,
        "update_type": "invoice_paid",
        "request_date": "2026-07-06T10:00:00Z",
        "payload": {
            "invoice_id": invoice_id,
            "status": "paid",
            "asset": "USDT",
            "amount": "3",
            "payload": str(internal_payment_id) if internal_payment_id else None,
        },
    }
    return json.dumps(update).encode()


async def test_webhook_bad_signature_rejected(client):
    await seed_pending_payment()
    body = webhook_body()
    resp = await client.post(
        WEBHOOK_PATH,
        content=body,
        headers={"crypto-pay-api-signature": "ff" * 32, "content-type": "application/json"},
    )
    assert resp.status_code == 401


async def test_webhook_wrong_secret_segment_404(client):
    body = webhook_body()
    resp = await client.post(
        "/payments/webhook/cryptobot/wrong",
        content=body,
        headers={"crypto-pay-api-signature": sign(body), "content-type": "application/json"},
    )
    assert resp.status_code == 404


async def test_webhook_activates_once_idempotent(client):
    payment_id = await seed_pending_payment()
    body = webhook_body(internal_payment_id=payment_id)
    headers = {"crypto-pay-api-signature": sign(body), "content-type": "application/json"}

    first = await client.post(WEBHOOK_PATH, content=body, headers=headers)
    assert first.status_code == 200, first.text

    async with get_session_factory()() as db:
        payment = await db.get(Payment, payment_id)
        assert payment.status == PaymentStatus.SUCCESS.value
        subs = (await db.scalars(select(Subscription))).all()
        assert len(subs) == 1
        first_expiry = subs[0].expires_at

    # Replay the exact same webhook — must be a no-op.
    second = await client.post(WEBHOOK_PATH, content=body, headers=headers)
    assert second.status_code == 200

    async with get_session_factory()() as db:
        count = await db.scalar(select(func.count(Subscription.id)))
        assert count == 1
        sub = await db.scalar(select(Subscription))
        assert sub.expires_at == first_expiry

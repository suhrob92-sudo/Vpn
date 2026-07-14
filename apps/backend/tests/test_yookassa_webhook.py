"""YooKassa webhook: IP allowlist + secret + authoritative GET re-check + idempotency."""
import json

import httpx
import respx
from sqlalchemy import func, select

from app.core.db import get_session_factory
from app.models import Payment, PaymentStatus, Plan, Subscription, User

WEBHOOK_PATH = "/payments/webhook/yookassa/ykhooksecret"
TRUSTED_IP = "185.71.76.1"        # inside 185.71.76.0/27
UNTRUSTED_IP = "8.8.8.8"
YK_ID = "2c85e2c0-000f-5000-8000-1234567890ab"


async def seed_pending_payment() -> int:
    async with get_session_factory()() as db:
        user = User(telegram_id=606, referral_code="ref606")
        plan = Plan(name="1 oylik", price=149, currency="RUB", duration_days=30)
        db.add_all([user, plan])
        await db.flush()
        payment = Payment(
            user_id=user.id,
            plan_id=plan.id,
            provider="yookassa",
            provider_payment_id=f"yookassa:{YK_ID}",
            amount=149,
            currency="RUB",
            status=PaymentStatus.PENDING.value,
        )
        db.add(payment)
        await db.commit()
        return payment.id


def webhook_body() -> bytes:
    return json.dumps(
        {
            "type": "notification",
            "event": "payment.succeeded",
            "object": {
                "id": YK_ID,
                "status": "succeeded",
                "amount": {"value": "149.00", "currency": "RUB"},
                "metadata": {"payment_id": "1"},
            },
        }
    ).encode()


def mock_status(respx_mock, status: str = "succeeded"):
    respx_mock.get(f"https://api.yookassa.ru/v3/payments/{YK_ID}").mock(
        return_value=httpx.Response(200, json={"id": YK_ID, "status": status})
    )


async def test_untrusted_ip_rejected(client):
    await seed_pending_payment()
    resp = await client.post(
        WEBHOOK_PATH,
        content=webhook_body(),
        headers={"x-forwarded-for": UNTRUSTED_IP, "content-type": "application/json"},
    )
    assert resp.status_code == 403


async def test_wrong_secret_404(client):
    resp = await client.post(
        "/payments/webhook/yookassa/wrong",
        content=webhook_body(),
        headers={"x-forwarded-for": TRUSTED_IP, "content-type": "application/json"},
    )
    assert resp.status_code == 404


@respx.mock
async def test_webhook_activates_once_idempotent(client, respx_mock):
    payment_id = await seed_pending_payment()
    mock_status(respx_mock, "succeeded")
    headers = {"x-forwarded-for": TRUSTED_IP, "content-type": "application/json"}

    first = await client.post(WEBHOOK_PATH, content=webhook_body(), headers=headers)
    assert first.status_code == 200, first.text
    async with get_session_factory()() as db:
        payment = await db.get(Payment, payment_id)
        assert payment.status == PaymentStatus.SUCCESS.value
        assert await db.scalar(select(func.count(Subscription.id))) == 1

    # Replay — must stay a single subscription.
    second = await client.post(WEBHOOK_PATH, content=webhook_body(), headers=headers)
    assert second.status_code == 200
    async with get_session_factory()() as db:
        assert await db.scalar(select(func.count(Subscription.id))) == 1


@respx.mock
async def test_webhook_ignored_when_recheck_not_succeeded(client, respx_mock):
    """A spoofed 'succeeded' body is neutralised by the GET re-check."""
    payment_id = await seed_pending_payment()
    mock_status(respx_mock, "pending")  # authoritative status disagrees
    resp = await client.post(
        WEBHOOK_PATH,
        content=webhook_body(),
        headers={"x-forwarded-for": TRUSTED_IP, "content-type": "application/json"},
    )
    assert resp.status_code == 200
    async with get_session_factory()() as db:
        payment = await db.get(Payment, payment_id)
        assert payment.status == PaymentStatus.PENDING.value  # NOT activated
        assert await db.scalar(select(func.count(Subscription.id))) == 0

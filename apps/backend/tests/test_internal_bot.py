"""Internal bot endpoints: HMAC auth, balance purchase, language persistence, connect."""
import hashlib
import hmac
import json
from decimal import Decimal

from sqlalchemy import select

from app.core.db import get_session_factory
from app.models import Plan, Subscription, SubscriptionStatus, User

SECRET = "test-jwt-secret"  # matches conftest JWT_SECRET


def sign(body: dict) -> tuple[bytes, dict]:
    raw = json.dumps(body).encode()
    sig = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return raw, {"x-internal-signature": sig, "content-type": "application/json"}


async def seed_user(balance: str = "0") -> tuple[int, int]:
    async with get_session_factory()() as db:
        user = User(telegram_id=4242, referral_code="ref4242", balance=Decimal(balance))
        plan = Plan(name="1 oylik", price=Decimal("149"), currency="RUB", duration_days=30)
        db.add_all([user, plan])
        await db.commit()
        return user.telegram_id, plan.id


async def test_bad_signature_rejected(client):
    resp = await client.post(
        "/internal/bot/set-language",
        content=b'{"telegram_id":1,"lang":"ru"}',
        headers={"x-internal-signature": "deadbeef", "content-type": "application/json"},
    )
    assert resp.status_code == 401


async def test_set_language_persists(client):
    tg_id, _ = await seed_user()
    raw, headers = sign({"telegram_id": tg_id, "lang": "ru"})
    resp = await client.post("/internal/bot/set-language", content=raw, headers=headers)
    assert resp.status_code == 200
    async with get_session_factory()() as db:
        user = await db.scalar(select(User).where(User.telegram_id == tg_id))
        assert user.language_code == "ru"


async def test_buy_from_balance_activates(client):
    tg_id, plan_id = await seed_user(balance="200")
    raw, headers = sign({"telegram_id": tg_id, "plan_id": plan_id})
    resp = await client.post("/internal/bot/buy-balance", content=raw, headers=headers)
    assert resp.status_code == 200, resp.text
    assert Decimal(resp.json()["data"]["balance"]) == Decimal("51")  # 200 - 149
    async with get_session_factory()() as db:
        sub = await db.scalar(select(Subscription))
        assert sub is not None and sub.status == SubscriptionStatus.ACTIVE.value


async def test_buy_from_balance_insufficient(client):
    tg_id, plan_id = await seed_user(balance="10")
    raw, headers = sign({"telegram_id": tg_id, "plan_id": plan_id})
    resp = await client.post("/internal/bot/buy-balance", content=raw, headers=headers)
    assert resp.status_code == 402
    async with get_session_factory()() as db:
        user = await db.scalar(select(User).where(User.telegram_id == tg_id))
        assert Decimal(user.balance) == Decimal("10")  # unchanged


async def test_connect_requires_active_sub(client):
    tg_id, _ = await seed_user()
    raw, headers = sign({"telegram_id": tg_id})
    resp = await client.post("/internal/bot/connect", content=raw, headers=headers)
    assert resp.status_code == 404  # no active subscription

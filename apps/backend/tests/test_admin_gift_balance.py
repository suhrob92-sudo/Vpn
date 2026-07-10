"""Admin gift subscriptions + wallet balance: top-up, deduction guard, pay-from-balance."""
from decimal import Decimal

from sqlalchemy import func, select

from app.core.db import get_session_factory
from app.core.security import create_token, hash_password
from app.models import (
    AdminUser,
    Payment,
    PaymentStatus,
    Plan,
    Subscription,
    SubscriptionStatus,
    User,
)


async def seed() -> tuple[int, int, str, str]:
    """Returns (user_id, plan_id, admin auth header, user auth header)."""
    async with get_session_factory()() as db:
        user = User(telegram_id=777, referral_code="ref777")
        plan = Plan(name="1 oylik", price=Decimal("149"), currency="RUB", duration_days=30)
        admin = AdminUser(username="root", password_hash=hash_password("x"), role="superadmin")
        db.add_all([user, plan, admin])
        await db.commit()
        admin_token = create_token(str(admin.id), "admin_access", 3600)
        user_token = create_token(str(user.id), "user", 3600)
        return user.id, plan.id, f"Bearer {admin_token}", f"Bearer {user_token}"


async def test_gift_creates_subscription_without_revenue(client):
    user_id, plan_id, admin_auth, _ = await seed()
    resp = await client.post(
        f"/admin/users/{user_id}/gift",
        json={"plan_id": plan_id},
        headers={"authorization": admin_auth},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["gifted"] is True

    async with get_session_factory()() as db:
        sub = await db.scalar(select(Subscription).where(Subscription.user_id == user_id))
        assert sub is not None and sub.status == SubscriptionStatus.ACTIVE.value
        payment = await db.scalar(select(Payment).where(Payment.user_id == user_id))
        assert payment.provider == "gift"
        assert payment.status == PaymentStatus.SUCCESS.value
        assert Decimal(payment.amount) == 0  # gifts never count as revenue


async def test_balance_topup_and_negative_guard(client):
    user_id, _, admin_auth, _ = await seed()
    resp = await client.post(
        f"/admin/users/{user_id}/balance",
        json={"amount": 500},
        headers={"authorization": admin_auth},
    )
    assert resp.status_code == 200, resp.text
    assert Decimal(resp.json()["data"]["balance"]) == 500

    # Deduction below zero must be rejected and leave the balance untouched.
    resp = await client.post(
        f"/admin/users/{user_id}/balance",
        json={"amount": -600},
        headers={"authorization": admin_auth},
    )
    assert resp.status_code == 409
    async with get_session_factory()() as db:
        user = await db.get(User, user_id)
        assert Decimal(user.balance) == 500


async def test_pay_from_balance(client):
    user_id, plan_id, admin_auth, user_auth = await seed()
    await client.post(
        f"/admin/users/{user_id}/balance",
        json={"amount": 200},
        headers={"authorization": admin_auth},
    )

    resp = await client.post(
        "/payments/balance/pay",
        json={"plan_id": plan_id},
        headers={"authorization": user_auth},
    )
    assert resp.status_code == 200, resp.text
    assert Decimal(resp.json()["data"]["balance"]) == Decimal("51")  # 200 - 149

    async with get_session_factory()() as db:
        sub_count = await db.scalar(select(func.count(Subscription.id)))
        assert sub_count == 1
        payment = await db.scalar(select(Payment).where(Payment.provider == "balance"))
        assert payment.status == PaymentStatus.SUCCESS.value

    # Second purchase must fail: 51 < 149.
    resp = await client.post(
        "/payments/balance/pay",
        json={"plan_id": plan_id},
        headers={"authorization": user_auth},
    )
    assert resp.status_code == 402
    async with get_session_factory()() as db:
        user = await db.get(User, user_id)
        assert Decimal(user.balance) == Decimal("51")


async def test_gift_requires_admin(client):
    user_id, plan_id, _, user_auth = await seed()
    resp = await client.post(
        f"/admin/users/{user_id}/gift",
        json={"plan_id": plan_id},
        headers={"authorization": user_auth},
    )
    assert resp.status_code == 401

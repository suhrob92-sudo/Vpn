"""Pre-expiry reminders: sent once per subscription period, only inside the window."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from app.core.db import get_session_factory
from app.models import Plan, Subscription, SubscriptionStatus, User
from app.worker import send_expiry_reminders


async def seed_sub(expires_in_days: float, telegram_id: int) -> int:
    now = datetime.now(timezone.utc)
    async with get_session_factory()() as db:
        user = User(telegram_id=telegram_id, referral_code=f"r{telegram_id}")
        plan = Plan(name="1 oylik", price=3, currency="USDT", duration_days=30)
        db.add_all([user, plan])
        await db.flush()
        sub = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE.value,
            started_at=now - timedelta(days=28),
            expires_at=now + timedelta(days=expires_in_days),
        )
        db.add(sub)
        await db.commit()
        return sub.id


async def test_reminder_sent_once_inside_window():
    sub_id = await seed_sub(expires_in_days=2, telegram_id=901)

    with patch("app.worker.send_message", new=AsyncMock(return_value=True)) as sent:
        assert await send_expiry_reminders({}) == 1
        assert await send_expiry_reminders({}) == 0  # already reminded

    assert sent.await_count == 1
    async with get_session_factory()() as db:
        sub = await db.get(Subscription, sub_id)
        assert sub.reminder_sent_at is not None


async def test_no_reminder_outside_window():
    await seed_sub(expires_in_days=10, telegram_id=902)
    with patch("app.worker.send_message", new=AsyncMock(return_value=True)) as sent:
        assert await send_expiry_reminders({}) == 0
    assert sent.await_count == 0

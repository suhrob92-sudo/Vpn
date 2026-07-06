"""Subscription expiration sweep: expired → 3X-UI client disabled → EXPIRED status."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from app.core.crypto import encrypt_secret
from app.core.db import get_session_factory
from app.models import (
    AccessStatus,
    Plan,
    Subscription,
    SubscriptionStatus,
    User,
    VpnAccess,
    VpnServer,
)
from app.worker import check_expired_subscriptions


async def seed_expired_subscription() -> tuple[int, int]:
    now = datetime.now(timezone.utc)
    async with get_session_factory()() as db:
        user = User(telegram_id=888, referral_code="ref888")
        plan = Plan(name="1 oylik", price=3, currency="USDT", duration_days=30)
        server = VpnServer(
            name="DE-1",
            country="DE",
            city="Frankfurt",
            panel_url="https://panel.test:2053/base",
            panel_user="admin",
            panel_pass_encrypted=encrypt_secret("panelpass"),
            inbound_id=1,
            host="1.2.3.4",
            port=443,
            public_key="pbk",
            short_id="sid",
            sni="yahoo.com",
        )
        db.add_all([user, plan, server])
        await db.flush()
        sub = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE.value,
            started_at=now - timedelta(days=31),
            expires_at=now - timedelta(hours=2),
        )
        db.add(sub)
        await db.flush()
        access = VpnAccess(
            user_id=user.id,
            subscription_id=sub.id,
            server_id=server.id,
            external_user_id="u1s1-abc",
            uuid="11111111-1111-1111-1111-111111111111",
            status=AccessStatus.ACTIVE.value,
        )
        db.add(access)
        await db.commit()
        return sub.id, access.id


async def test_expired_subscription_is_revoked_and_marked():
    sub_id, access_id = await seed_expired_subscription()

    fake_panel = AsyncMock()
    with (
        patch("app.services.vpn_manager.manager.panel_client", return_value=fake_panel),
        patch("app.worker.send_message", new=AsyncMock(return_value=True)) as sent,
    ):
        processed = await check_expired_subscriptions({})

    assert processed == 1
    # Panel client was told to disable the client
    assert fake_panel.update_client.await_count == 1
    kwargs = fake_panel.update_client.await_args.kwargs
    assert kwargs["enable"] is False
    # User got notified
    assert sent.await_count == 1

    async with get_session_factory()() as db:
        sub = await db.get(Subscription, sub_id)
        access = await db.get(VpnAccess, access_id)
        assert sub.status == SubscriptionStatus.EXPIRED.value
        assert access.status == AccessStatus.REVOKED.value
        assert access.revoked_at is not None


async def test_active_subscription_untouched():
    now = datetime.now(timezone.utc)
    async with get_session_factory()() as db:
        user = User(telegram_id=889, referral_code="ref889")
        plan = Plan(name="1 oylik", price=3, currency="USDT", duration_days=30)
        db.add_all([user, plan])
        await db.flush()
        sub = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE.value,
            started_at=now,
            expires_at=now + timedelta(days=10),
        )
        db.add(sub)
        await db.commit()
        sub_id = sub.id

    processed = await check_expired_subscriptions({})
    assert processed == 0
    async with get_session_factory()() as db:
        sub = await db.get(Subscription, sub_id)
        assert sub.status == SubscriptionStatus.ACTIVE.value

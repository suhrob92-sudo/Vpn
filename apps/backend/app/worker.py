"""ARQ background worker.

Jobs:
- check_expired_subscriptions — hourly cron: expired subs → revoke 3X-UI clients,
  mark EXPIRED, notify the user in Telegram; critical failures alert the admin chat.
- sync_traffic — optional periodic traffic refresh hook (best effort).
"""
import logging
from datetime import datetime, timezone

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import get_session_factory
from app.core.logging import setup_logging
from app.models import (
    AccessStatus,
    Subscription,
    SubscriptionStatus,
    User,
    VpnAccess,
    VpnServer,
)
from app.services.telegram import notify_admin, send_message
from app.services.vpn_manager import revoke_access

logger = logging.getLogger(__name__)

EXPIRED_MESSAGE = (
    "⏳ <b>Obunangiz muddati tugadi</b>\n\n"
    "VPN ulanishingiz to'xtatildi. Xizmatdan yana foydalanish uchun "
    "obunani uzaytiring: bot menyusidan «💎 Tariflar» bo'limini oching."
)


async def check_expired_subscriptions(ctx: dict) -> int:
    """Expire overdue subscriptions and revoke their VPN accesses. Returns count."""
    now = datetime.now(timezone.utc)
    processed = 0
    async with get_session_factory()() as db:
        subs = (
            await db.scalars(
                select(Subscription).where(
                    Subscription.status == SubscriptionStatus.ACTIVE.value,
                    Subscription.expires_at <= now,
                )
            )
        ).all()
        for sub in subs:
            try:
                rows = (
                    await db.execute(
                        select(VpnAccess, VpnServer)
                        .join(VpnServer, VpnAccess.server_id == VpnServer.id)
                        .where(
                            VpnAccess.subscription_id == sub.id,
                            VpnAccess.status == AccessStatus.ACTIVE.value,
                        )
                    )
                ).all()
                for access, server in rows:
                    await revoke_access(db, access, server)
                sub.status = SubscriptionStatus.EXPIRED.value
                await db.commit()
                processed += 1

                user = await db.get(User, sub.user_id)
                if user:
                    await send_message(user.telegram_id, EXPIRED_MESSAGE)
            except Exception as exc:  # noqa: BLE001 — keep sweeping other subs
                await db.rollback()
                logger.exception("expiry sweep failed for subscription %s", sub.id)
                await notify_admin(f"Expiry sweep failed for subscription {sub.id}: {exc}")
    if processed:
        logger.info("expired %s subscriptions", processed)
    return processed


async def sync_traffic(ctx: dict) -> None:
    """Placeholder-free hook: traffic is read live from the panel API on demand
    (profile/connect endpoints); a periodic cache refresh can be added here
    when usage warrants it."""
    return None


async def startup(ctx: dict) -> None:
    setup_logging()
    logger.info("worker started")


class WorkerSettings:
    functions = [check_expired_subscriptions, sync_traffic]
    cron_jobs = [
        cron(check_expired_subscriptions, minute=7),  # hourly at :07
    ]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)

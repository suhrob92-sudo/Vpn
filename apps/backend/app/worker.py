"""ARQ background worker.

Jobs:
- check_expired_subscriptions — hourly cron: expired subs → revoke 3X-UI clients,
  mark EXPIRED, notify the user in Telegram; critical failures alert the admin chat.
- sync_traffic — optional periodic traffic refresh hook (best effort).
"""
import logging
from datetime import datetime, timedelta, timezone

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import get_session_factory
from app.core.logging import setup_logging
from app.core.time import aware_utc
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

EXPIRED_MESSAGE = {
    "uz": (
        "⏳ <b>Obunangiz muddati tugadi</b>\n\n"
        "VPN ulanishingiz to'xtatildi. Xizmatdan yana foydalanish uchun "
        "obunani uzaytiring: bot menyusidan «💎 Tariflar» bo'limini oching."
    ),
    "ru": (
        "⏳ <b>Ваша подписка истекла</b>\n\n"
        "VPN-подключение отключено. Чтобы продолжить пользоваться сервисом, "
        "продлите подписку: откройте «💎 Тарифы» в меню бота."
    ),
    "en": (
        "⏳ <b>Your subscription has expired</b>\n\n"
        "Your VPN connection has been stopped. To keep using the service, "
        "renew your plan: open “💎 Plans” from the bot menu."
    ),
}

REMINDER_MESSAGE = {
    "uz": (
        "🔔 <b>Eslatma:</b> obunangiz tugashiga <b>{days} kun</b> qoldi "
        "({date} gacha).\n\nUzluksiz ishlashi uchun obunani hozir uzaytiring."
    ),
    "ru": (
        "🔔 <b>Напоминание:</b> до конца подписки осталось <b>{days} дней</b> "
        "(до {date}).\n\nПродлите подписку сейчас, чтобы не было перерыва."
    ),
    "en": (
        "🔔 <b>Reminder:</b> <b>{days} days</b> left on your subscription "
        "(until {date}).\n\nRenew now to avoid any interruption."
    ),
}


def _lang(user: User) -> str:
    c = (user.language_code or "").lower()
    if c.startswith("ru"):
        return "ru"
    if c.startswith("en"):
        return "en"
    return "uz"


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
                    await send_message(user.telegram_id, EXPIRED_MESSAGE[_lang(user)])
            except Exception as exc:  # noqa: BLE001 — keep sweeping other subs
                await db.rollback()
                logger.exception("expiry sweep failed for subscription %s", sub.id)
                await notify_admin(f"Expiry sweep failed for subscription {sub.id}: {exc}")
    if processed:
        logger.info("expired %s subscriptions", processed)
    return processed


async def send_expiry_reminders(ctx: dict) -> int:
    """Warn users whose subscription expires within `expiry_reminder_days`.
    Sent once per subscription period (reminder_sent_at resets on renewal)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(days=settings.expiry_reminder_days)
    sent = 0
    async with get_session_factory()() as db:
        subs = (
            await db.scalars(
                select(Subscription).where(
                    Subscription.status == SubscriptionStatus.ACTIVE.value,
                    Subscription.expires_at > now,
                    Subscription.expires_at <= window_end,
                    Subscription.reminder_sent_at.is_(None),
                )
            )
        ).all()
        for sub in subs:
            user = await db.get(User, sub.user_id)
            if user is None:
                continue
            expires = aware_utc(sub.expires_at)
            days_left = max(1, (expires - now).days or 1)
            delivered = await send_message(
                user.telegram_id,
                REMINDER_MESSAGE[_lang(user)].format(
                    days=days_left, date=expires.strftime("%d.%m.%Y")
                ),
            )
            if delivered:
                sub.reminder_sent_at = now
                await db.commit()
                sent += 1
            else:
                await db.rollback()
    if sent:
        logger.info("sent %s expiry reminders", sent)
    return sent


async def sync_traffic(ctx: dict) -> None:
    """Placeholder-free hook: traffic is read live from the panel API on demand
    (profile/connect endpoints); a periodic cache refresh can be added here
    when usage warrants it."""
    return None


async def startup(ctx: dict) -> None:
    setup_logging()
    logger.info("worker started")


class WorkerSettings:
    functions = [check_expired_subscriptions, send_expiry_reminders, sync_traffic]
    cron_jobs = [
        cron(check_expired_subscriptions, minute=7),          # hourly at :07
        cron(send_expiry_reminders, hour=9, minute=30),       # daily at 09:30 UTC
    ]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)

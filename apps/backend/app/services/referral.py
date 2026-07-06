"""Referral rewards (v1.1).

Rule: when an invited user's FIRST payment activates, the inviter earns
`referral_bonus_days` extra days. If the inviter has an active subscription the
bonus is applied immediately (panel expiry is pushed too); otherwise the event
becomes REWARD_PENDING and is applied the next time the inviter's own
subscription activates.

Event statuses: TRACKED → REWARDED | REWARD_PENDING → REWARDED.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.time import aware_utc
from app.models import (
    AccessStatus,
    Payment,
    PaymentStatus,
    ReferralEvent,
    Subscription,
    SubscriptionStatus,
    User,
    VpnAccess,
    VpnServer,
)
from app.services.telegram import send_message
from app.services.vpn_manager import renew_access

logger = logging.getLogger(__name__)

STATUS_TRACKED = "TRACKED"
STATUS_REWARD_PENDING = "REWARD_PENDING"
STATUS_REWARDED = "REWARDED"

REWARD_MESSAGE = (
    "🎁 <b>Referral bonus!</b>\n\n"
    "Siz taklif qilgan foydalanuvchi obuna sotib oldi — "
    "obunangizga <b>{days} kun</b> qo'shildi. Rahmat!"
)


async def _extend_subscription(db: AsyncSession, user: User, days: int) -> bool:
    """Extend the user's active subscription locally and on the panels.
    Returns False when there is nothing to extend."""
    now = datetime.now(timezone.utc)
    sub = await db.scalar(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.expires_at > now,
        )
    )
    if sub is None:
        return False
    sub.expires_at = aware_utc(sub.expires_at) + timedelta(days=days)
    sub.reminder_sent_at = None  # expiry moved — reminder becomes relevant again
    await db.flush()

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
    traffic_gb = sub.plan.traffic_limit_gb if sub.plan else 0
    for access, server in rows:
        try:
            await renew_access(db, access, server, sub.expires_at, traffic_gb)
        except Exception as exc:  # noqa: BLE001 — panel hiccup must not void the bonus
            logger.error("referral: panel expiry push failed (access=%s): %s", access.id, exc)
    return True


async def apply_referral_reward_on_payment(db: AsyncSession, invited: User) -> None:
    """Called after a payment activates for `invited`. Rewards the inviter once,
    on the invited user's first successful payment only."""
    if invited.referred_by is None:
        return
    paid_count = await db.scalar(
        select(func.count(Payment.id)).where(
            Payment.user_id == invited.id,
            Payment.status == PaymentStatus.SUCCESS.value,
        )
    )
    if paid_count != 1:  # renewals never re-trigger the reward
        return
    event = await db.scalar(
        select(ReferralEvent).where(
            ReferralEvent.invited_user_id == invited.id,
            ReferralEvent.inviter_id == invited.referred_by,
            ReferralEvent.status == STATUS_TRACKED,
        )
    )
    if event is None:
        return
    inviter = await db.get(User, invited.referred_by)
    if inviter is None:
        return

    days = get_settings().referral_bonus_days
    if await _extend_subscription(db, inviter, days):
        event.status = STATUS_REWARDED
        await db.flush()
        await send_message(inviter.telegram_id, REWARD_MESSAGE.format(days=days))
        logger.info("referral reward applied: inviter=%s +%sd", inviter.id, days)
    else:
        event.status = STATUS_REWARD_PENDING
        await db.flush()
        logger.info("referral reward pending: inviter=%s has no active sub", inviter.id)


async def apply_pending_rewards(db: AsyncSession, user: User) -> int:
    """Called when `user`'s own subscription activates: cash in any rewards
    earned while they had no active subscription. Returns days applied."""
    events = (
        await db.scalars(
            select(ReferralEvent).where(
                ReferralEvent.inviter_id == user.id,
                ReferralEvent.status == STATUS_REWARD_PENDING,
            )
        )
    ).all()
    if not events:
        return 0
    days = get_settings().referral_bonus_days * len(events)
    if not await _extend_subscription(db, user, days):
        return 0
    for event in events:
        event.status = STATUS_REWARDED
    await db.flush()
    await send_message(user.telegram_id, REWARD_MESSAGE.format(days=days))
    logger.info("pending referral rewards applied: user=%s +%sd", user.id, days)
    return days

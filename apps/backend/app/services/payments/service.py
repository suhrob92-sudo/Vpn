"""Payment orchestration: invoice creation, webhook handling, idempotent activation.

Activation is strictly webhook-driven — the frontend success page has no effect.
Idempotency: payments.provider_payment_id is UNIQUE and activation is a no-op
when the payment is already SUCCESS, so replayed webhooks cannot double-activate.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import aware_utc
from app.models import (
    Payment,
    PaymentStatus,
    Plan,
    ServerStatus,
    Subscription,
    SubscriptionStatus,
    User,
    VpnServer,
)
from app.services.payments.base import PaymentProvider
from app.services.payments.cryptobot import CryptoBotProvider
from app.services.referral import apply_pending_rewards, apply_referral_reward_on_payment
from app.services.subscription import ensure_token
from app.services.vpn_manager import create_access
from app.services.vpn_manager.xui_client import XuiError

logger = logging.getLogger(__name__)


def get_provider(name: str) -> PaymentProvider:
    if name == "cryptobot":
        return CryptoBotProvider()
    raise ValueError(f"unknown payment provider: {name}")


async def create_payment(db: AsyncSession, user: User, plan: Plan, provider_name: str) -> Payment:
    provider = get_provider(provider_name)
    payment = Payment(
        user_id=user.id,
        plan_id=plan.id,
        provider=provider.name,
        amount=plan.price,
        currency=plan.currency,
        status=PaymentStatus.PENDING.value,
    )
    db.add(payment)
    await db.flush()  # get payment.id for the provider payload

    invoice = await provider.create_invoice(
        amount=Decimal(plan.price),
        currency=plan.currency,
        description=f"VPN plan: {plan.name} ({plan.duration_days} days)",
        internal_payment_id=payment.id,
    )
    payment.provider_payment_id = invoice.provider_payment_id
    payment.invoice_url = invoice.invoice_url
    await db.flush()
    return payment


async def activate_payment(db: AsyncSession, payment: Payment) -> Subscription | None:
    """Mark payment SUCCESS and create/extend the subscription + VPN access.

    Idempotent: if the payment is already SUCCESS nothing happens.
    Returns the subscription (None when skipped as duplicate).
    """
    if payment.status == PaymentStatus.SUCCESS.value:
        logger.info("payment %s already activated — duplicate webhook ignored", payment.id)
        return None

    now = datetime.now(timezone.utc)
    payment.status = PaymentStatus.SUCCESS.value
    payment.paid_at = now

    plan = await db.get(Plan, payment.plan_id)
    assert plan is not None

    user = await db.get(User, payment.user_id)
    assert user is not None

    # Extend an active subscription, otherwise start a new one.
    sub = await db.scalar(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE.value,
        )
    )
    duration = timedelta(days=plan.duration_days)
    if sub and aware_utc(sub.expires_at) > now:
        sub.plan_id = plan.id
        sub.expires_at = aware_utc(sub.expires_at) + duration
        sub.reminder_sent_at = None
    elif sub:
        sub.plan_id = plan.id
        sub.started_at = now
        sub.expires_at = now + duration
        sub.reminder_sent_at = None
    else:
        sub = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE.value,
            started_at=now,
            expires_at=now + duration,
        )
        db.add(sub)
    await db.flush()

    await ensure_token(db, user)
    await provision_subscription(db, user, sub, plan)

    # Referral rewards (v1.1): reward the inviter on this user's first payment,
    # and cash in any rewards this user earned while having no active sub.
    await apply_referral_reward_on_payment(db, user)
    await apply_pending_rewards(db, user)
    return sub


async def provision_subscription(
    db: AsyncSession, user: User, sub: Subscription, plan: Plan
) -> list[int]:
    """Create/renew a 3X-UI client on every ONLINE server.

    Returns ids of servers where provisioning failed (caller alerts admin /
    schedules a retry); failures never roll back the payment activation.
    """
    servers = (
        await db.scalars(
            select(VpnServer).where(VpnServer.status == ServerStatus.ONLINE.value)
        )
    ).all()
    failed: list[int] = []
    for server in servers:
        try:
            await create_access(db, user, sub, server, plan.traffic_limit_gb)
        except (XuiError, Exception) as exc:  # noqa: BLE001 — keep other servers going
            logger.error("provisioning failed on server %s: %s", server.id, exc)
            failed.append(server.id)
    return failed


# ── Webhook handlers ────────────────────────────────────────────────────────

async def handle_cryptobot_webhook(db: AsyncSession, raw_body: bytes) -> Subscription | None:
    """Process a signature-verified CryptoBot update (invoice_paid)."""
    update = json.loads(raw_body)
    if update.get("update_type") != "invoice_paid":
        return None
    invoice = update.get("payload") or {}
    provider_payment_id = f"cryptobot:{invoice.get('invoice_id')}"

    payment = await db.scalar(
        select(Payment).where(Payment.provider_payment_id == provider_payment_id)
    )
    if payment is None:
        # Fall back to our internal id passed in the invoice payload field.
        internal_id = invoice.get("payload")
        payment = await db.get(Payment, int(internal_id)) if internal_id else None
    if payment is None:
        logger.warning("webhook for unknown invoice %s", provider_payment_id)
        return None
    return await activate_payment(db, payment)


async def handle_stars_payment(
    db: AsyncSession,
    user_telegram_id: int,
    plan_id: int,
    charge_id: str,
    amount: int,
) -> Subscription | None:
    """Telegram Stars: the bot receives `successful_payment` (authenticated by
    Telegram itself) and reports it here. Idempotent by charge id."""
    provider_payment_id = f"stars:{charge_id}"
    existing = await db.scalar(
        select(Payment).where(Payment.provider_payment_id == provider_payment_id)
    )
    if existing:
        return await activate_payment(db, existing)  # no-op if already SUCCESS

    user = await db.scalar(select(User).where(User.telegram_id == user_telegram_id))
    plan = await db.get(Plan, plan_id)
    if user is None or plan is None:
        logger.warning("stars payment for unknown user/plan: %s/%s", user_telegram_id, plan_id)
        return None
    payment = Payment(
        user_id=user.id,
        plan_id=plan.id,
        provider="stars",
        provider_payment_id=provider_payment_id,
        amount=Decimal(amount),
        currency="XTR",
        status=PaymentStatus.PENDING.value,
    )
    db.add(payment)
    await db.flush()
    return await activate_payment(db, payment)

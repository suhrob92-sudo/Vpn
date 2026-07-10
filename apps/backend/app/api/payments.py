"""Payment endpoints: invoice creation + provider webhooks."""
import hashlib
import hmac
import json
import logging
import uuid as uuidlib
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.core.ratelimit import rate_limit
from app.models import Payment, PaymentStatus, Plan, User
from app.schemas.billing import PaymentCreateIn, PaymentOut
from app.schemas.common import ok
from app.services.telegram import create_stars_invoice_link
from app.services.payments import (
    CryptoBotProvider,
    activate_payment,
    create_payment,
    handle_cryptobot_webhook,
    handle_stars_payment,
    handle_yookassa_webhook,
    is_trusted_ip,
)

# Providers whose invoices can be created from the Mini App (card/crypto with a
# hosted payment page). Stars are created by the bot, not here.
_API_PROVIDERS = {"yookassa", "cryptobot"}

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/create", dependencies=[Depends(rate_limit("payments", limit=10))])
async def create(
    body: PaymentCreateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(Plan, body.plan_id)
    if plan is None or not plan.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    provider = body.provider or get_settings().default_payment_provider
    if provider not in _API_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider must be one of {sorted(_API_PROVIDERS)}; Stars go through the bot",
        )
    payment = await create_payment(db, user, plan, provider)
    await db.commit()
    return ok(PaymentOut.model_validate(payment).model_dump(mode="json"))


@router.post("/stars/create", dependencies=[Depends(rate_limit("payments", limit=10))])
async def create_stars_invoice(
    body: PaymentCreateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a Telegram Stars invoice link for the Mini App to open with
    WebApp.openInvoice(). Activation happens when the bot receives the
    resulting `successful_payment` (idempotent by charge id)."""
    plan = await db.get(Plan, body.plan_id)
    if plan is None or not plan.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if plan.price_stars <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This plan is not available for Stars payment",
        )
    link = await create_stars_invoice_link(
        title=f"VPN — {plan.name}",
        description=plan.description or f"{plan.duration_days} kunlik VPN obuna",
        payload=f"plan:{plan.id}",
        stars_amount=plan.price_stars,
    )
    return ok({"invoice_link": link})


@router.post("/balance/pay", dependencies=[Depends(rate_limit("payments", limit=10))])
async def pay_from_balance(
    body: PaymentCreateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Buy a plan with the internal wallet (topped up by admins). Deduction and
    activation happen in one transaction — a provisioning hiccup never leaves
    the user charged without a subscription."""
    plan = await db.get(Plan, body.plan_id)
    if plan is None or not plan.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if Decimal(user.balance) < Decimal(plan.price):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Balansingiz yetarli emas",
        )

    user.balance = Decimal(user.balance) - Decimal(plan.price)
    payment = Payment(
        user_id=user.id,
        plan_id=plan.id,
        provider="balance",
        provider_payment_id=f"balance:{uuidlib.uuid4()}",
        amount=plan.price,
        currency=plan.currency,
        status=PaymentStatus.PENDING.value,
    )
    db.add(payment)
    await db.flush()
    sub = await activate_payment(db, payment)
    await db.commit()
    return ok(
        {
            "paid": True,
            "balance": str(user.balance),
            "expires_at": sub.expires_at.isoformat() if sub else None,
        }
    )


@router.get("/{payment_id}")
async def get_payment(
    payment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payment = await db.get(Payment, payment_id)
    if payment is None or payment.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return ok(PaymentOut.model_validate(payment).model_dump(mode="json"))


@router.post("/webhook/cryptobot/{secret}")
async def cryptobot_webhook(secret: str, request: Request, db: AsyncSession = Depends(get_db)):
    """CryptoBot webhook. Defense in depth: secret URL segment + HMAC signature
    + idempotent activation (unique provider_payment_id)."""
    settings = get_settings()
    if not hmac.compare_digest(secret, settings.cryptobot_webhook_secret):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    raw_body = await request.body()
    signature = request.headers.get("crypto-pay-api-signature", "")
    if not CryptoBotProvider().verify_webhook(raw_body, signature):
        logger.warning("cryptobot webhook: bad signature")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bad signature")

    await handle_cryptobot_webhook(db, raw_body)
    await db.commit()
    return ok({"received": True})


@router.post("/webhook/yookassa/{secret}")
async def yookassa_webhook(secret: str, request: Request, db: AsyncSession = Depends(get_db)):
    """YooKassa notification. YooKassa does not sign the body, so genuineness is
    established by three independent checks: secret URL segment, source-IP
    allowlist, and an authoritative GET re-check of the payment inside the
    handler. Activation stays idempotent (unique provider_payment_id)."""
    settings = get_settings()
    if not hmac.compare_digest(secret, settings.yookassa_webhook_secret):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else None
    )
    if not is_trusted_ip(client_ip):
        logger.warning("yookassa webhook from untrusted ip: %s", client_ip)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="untrusted source")

    raw_body = await request.body()
    await handle_yookassa_webhook(db, raw_body)
    await db.commit()
    return ok({"received": True})


@router.post("/webhook/stars")
async def stars_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Internal endpoint for the bot process reporting a Telegram Stars
    `successful_payment`. Authenticated with an HMAC over the raw body using
    JWT_SECRET (shared platform secret, never exposed publicly)."""
    raw_body = await request.body()
    signature = request.headers.get("x-internal-signature", "")
    expected = hmac.new(
        get_settings().jwt_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bad signature")

    data = json.loads(raw_body)
    await handle_stars_payment(
        db,
        user_telegram_id=data["telegram_id"],
        plan_id=data["plan_id"],
        charge_id=data["charge_id"],
        amount=data["amount"],
    )
    await db.commit()
    return ok({"received": True})

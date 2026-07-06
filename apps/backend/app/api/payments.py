"""Payment endpoints: invoice creation + provider webhooks."""
import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.core.ratelimit import rate_limit
from app.models import Payment, Plan, User
from app.schemas.billing import PaymentCreateIn, PaymentOut
from app.schemas.common import ok
from app.services.payments import (
    CryptoBotProvider,
    create_payment,
    handle_cryptobot_webhook,
    handle_stars_payment,
)

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
    if body.provider != "cryptobot":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only cryptobot payments are created via API; Stars go through the bot",
        )
    payment = await create_payment(db, user, plan, body.provider)
    await db.commit()
    return ok(PaymentOut.model_validate(payment).model_dump(mode="json"))


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

"""Internal endpoints for the bot process.

Auth: X-Internal-Signature = HMAC-SHA256(raw_body, JWT_SECRET). The bot and the
backend share JWT_SECRET via env; these endpoints are never exposed through Caddy.
"""
import hashlib
import hmac
import json
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.models import Payment, PaymentStatus, Plan, Subscription, SubscriptionStatus, User
from app.schemas.billing import PlanOut, SubscriptionOut
from app.schemas.common import ok
from app.schemas.user import UserOut
from app.services.payments import activate_payment
from app.services.subscription import ensure_token, subscription_url
from app.services.users import upsert_from_telegram
import uuid as uuidlib

router = APIRouter(prefix="/internal/bot", tags=["internal"])


async def _verified_body(request: Request) -> dict:
    raw = await request.body()
    signature = request.headers.get("x-internal-signature", "")
    expected = hmac.new(get_settings().jwt_secret.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bad signature")
    return json.loads(raw)


@router.post("/users")
async def bot_upsert_user(request: Request, db: AsyncSession = Depends(get_db)):
    """Called on /start: upsert user + track referral deep-link param."""
    body = await _verified_body(request)
    tg_user = body["telegram_user"]
    user = await upsert_from_telegram(db, tg_user, body.get("start_param"))
    await db.commit()
    return ok(UserOut.model_validate(user).model_dump(mode="json"))


@router.post("/profile")
async def bot_profile(request: Request, db: AsyncSession = Depends(get_db)):
    """Profile summary for /profile and /subscription commands."""
    body = await _verified_body(request)
    user = await db.scalar(select(User).where(User.telegram_id == body["telegram_id"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    sub = await db.scalar(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.expires_at.desc())
        .limit(1)
    )
    connect_url = None
    days_left = 0
    if sub and sub.status == SubscriptionStatus.ACTIVE.value:
        now = datetime.now(timezone.utc)
        days_left = max(0, (sub.expires_at - now).days)
        _, raw_token = await ensure_token(db, user)
        await db.commit()
        connect_url = subscription_url(raw_token)

    return ok(
        {
            "user": UserOut.model_validate(user).model_dump(mode="json"),
            "subscription": (
                SubscriptionOut.model_validate(sub).model_dump(mode="json") if sub else None
            ),
            "days_left": days_left,
            "connect_url": connect_url,
        }
    )


@router.post("/plans")
async def bot_plans(request: Request, db: AsyncSession = Depends(get_db)):
    await _verified_body(request)
    plans = (
        await db.scalars(
            select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort_order, Plan.id)
        )
    ).all()
    return ok([PlanOut.model_validate(p).model_dump(mode="json") for p in plans])


@router.post("/connect")
async def bot_connect(request: Request, db: AsyncSession = Depends(get_db)):
    """Connect info for the fully in-bot flow: stable subscription URL + deep links.
    Returns 404 when the user has no active subscription."""
    body = await _verified_body(request)
    user = await db.scalar(select(User).where(User.telegram_id == body["telegram_id"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    sub = await db.scalar(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE.value,
        )
    )
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription")
    _, raw_token = await ensure_token(db, user)
    await db.commit()
    url = subscription_url(raw_token)
    return ok(
        {
            "subscription_url": url,
            "deep_links": {
                "v2rayng": f"v2rayng://install-sub?url={quote(url, safe='')}&name=VPN",
                "happ": f"happ://add/{url}",
            },
        }
    )


@router.post("/buy-balance")
async def bot_buy_balance(request: Request, db: AsyncSession = Depends(get_db)):
    """Buy a plan from the user's internal wallet, entirely inside the bot."""
    body = await _verified_body(request)
    user = await db.scalar(select(User).where(User.telegram_id == body["telegram_id"]))
    plan = await db.get(Plan, int(body["plan_id"]))
    if user is None or plan is None or not plan.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User or plan not found")
    if Decimal(user.balance) < Decimal(plan.price):
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="insufficient balance")

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
    return ok({"paid": True, "balance": str(user.balance), "plan": plan.name,
               "expires_at": sub.expires_at.isoformat() if sub else None})


@router.post("/set-language")
async def bot_set_language(request: Request, db: AsyncSession = Depends(get_db)):
    """Persist the user's chosen bot/app language (uz|ru|en)."""
    body = await _verified_body(request)
    lang = body.get("lang")
    if lang not in ("uz", "ru", "en"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="bad lang")
    user = await db.scalar(select(User).where(User.telegram_id == body["telegram_id"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.language_code = lang
    await db.commit()
    return ok({"lang": lang})

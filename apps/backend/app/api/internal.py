"""Internal endpoints for the bot process.

Auth: X-Internal-Signature = HMAC-SHA256(raw_body, JWT_SECRET). The bot and the
backend share JWT_SECRET via env; these endpoints are never exposed through Caddy.
"""
import hashlib
import hmac
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.models import Plan, Subscription, SubscriptionStatus, User
from app.schemas.billing import PlanOut, SubscriptionOut
from app.schemas.common import ok
from app.schemas.user import UserOut
from app.services.subscription import ensure_token, subscription_url
from app.services.users import upsert_from_telegram

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

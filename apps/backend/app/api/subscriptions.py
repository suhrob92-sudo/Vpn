from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.core.ratelimit import rate_limit
from app.models import Plan, Subscription, SubscriptionStatus, User
from app.schemas.billing import PaymentOut, SubscriptionOut
from app.schemas.common import ok
from app.services.payments import create_payment, provider_configured

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/me")
async def my_subscription(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    sub = await db.scalar(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.expires_at.desc())
        .limit(1)
    )
    if sub is None:
        return ok(None)
    return ok(SubscriptionOut.model_validate(sub).model_dump(mode="json"))


@router.post("/renew", dependencies=[Depends(rate_limit("payments", limit=10))])
async def renew(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Renewal = a fresh invoice for the user's current plan; activation happens
    on the payment webhook, extending the existing subscription."""
    sub = await db.scalar(
        select(Subscription)
        .where(
            Subscription.user_id == user.id,
            Subscription.status.in_(
                [SubscriptionStatus.ACTIVE.value, SubscriptionStatus.EXPIRED.value]
            ),
        )
        .order_by(Subscription.expires_at.desc())
        .limit(1)
    )
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Nothing to renew — buy a plan first"
        )
    plan = await db.get(Plan, sub.plan_id)
    if plan is None or not plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Current plan is unavailable — choose a new plan",
        )
    provider = get_settings().default_payment_provider
    if not provider_configured(provider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Karta to'lovi hozircha ulanmagan — Stars yoki balansdan foydalaning",
        )
    payment = await create_payment(db, user, plan, provider)
    await db.commit()
    return ok(PaymentOut.model_validate(payment).model_dump(mode="json"))

"""Current user profile + connect info."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import AccessStatus, Subscription, SubscriptionStatus, User, VpnAccess, VpnServer
from app.schemas.common import ok
from app.schemas.user import UserOut, UserPatch
from app.services.subscription import ensure_token, subscription_url
from app.services.vpn_manager import get_traffic

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return ok(UserOut.model_validate(user).model_dump(mode="json"))


@router.patch("/me")
async def patch_me(
    body: UserPatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.language_code is not None:
        user.language_code = body.language_code
    await db.commit()
    return ok(UserOut.model_validate(user).model_dump(mode="json"))


@router.get("/me/connect")
async def connect_info(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Everything the Connect screen needs: stable subscription URL, deep links, traffic."""
    sub = await db.scalar(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE.value,
        )
    )
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription"
        )

    _, raw_token = await ensure_token(db, user)
    await db.commit()
    url = subscription_url(raw_token)

    # Aggregate traffic over the user's accesses (best effort, panel API).
    rows = (
        await db.execute(
            select(VpnAccess, VpnServer)
            .join(VpnServer, VpnAccess.server_id == VpnServer.id)
            .where(
                VpnAccess.user_id == user.id,
                VpnAccess.status == AccessStatus.ACTIVE.value,
            )
        )
    ).all()
    up = down = 0
    for access, server in rows:
        stats = await get_traffic(access, server)
        if stats:
            up += stats.get("up", 0) or 0
            down += stats.get("down", 0) or 0

    return ok(
        {
            "subscription_url": url,
            "deep_links": {
                # v2rayNG scheme verified in 2dust/v2rayNG; Happ per happ.su dev docs
                "v2rayng": f"v2rayng://install-sub?url={quote(url, safe='')}&name=VPN",
                "happ": f"happ://add/{url}",
            },
            "traffic": {"up": up, "down": down},
        }
    )

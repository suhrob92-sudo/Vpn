"""Universal subscription endpoint — consumed by VPN clients, not browsers."""
import base64

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.ratelimit import rate_limit
from app.services.subscription import build_subscription_body, resolve_token
from app.services.vpn_manager import get_config_links

router = APIRouter(tags=["subscription"])


@router.get("/sub/{token}", dependencies=[Depends(rate_limit("sub", limit=60))])
async def get_subscription(token: str, db: AsyncSession = Depends(get_db)):
    user = await resolve_token(db, token)
    if user is None:
        # No hints: invalid, revoked and expired all look identical.
        return Response(status_code=404)
    links = await get_config_links(db, user)
    await db.commit()
    if not links:
        return Response(status_code=404)

    body = build_subscription_body(links)
    title = base64.b64encode(b"VPN").decode()
    return Response(
        content=body,
        media_type="text/plain",
        headers={
            "profile-title": f"base64:{title}",
            "profile-update-interval": "12",
        },
    )

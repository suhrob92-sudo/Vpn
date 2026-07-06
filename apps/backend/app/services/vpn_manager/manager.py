"""VPN Management Service — business operations on top of the 3X-UI wrapper.

create_access / revoke_access / renew_access / get_traffic / get_config_links.
One 3X-UI client per (user, server); multi-server subscriptions get one access
row per server and the subscription endpoint merges all config links.
"""
import logging
import secrets
import uuid as uuidlib
from datetime import datetime, timezone
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret
from app.models import (
    AccessStatus,
    Subscription,
    User,
    VpnAccess,
    VpnServer,
)
from app.services.vpn_manager.xui_client import XuiClient, XuiError

logger = logging.getLogger(__name__)

GB = 1024**3


def panel_client(server: VpnServer) -> XuiClient:
    return XuiClient(
        panel_url=server.panel_url,
        username=server.panel_user,
        password=decrypt_secret(server.panel_pass_encrypted),
    )


def _expiry_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _client_email(user: User, server: VpnServer) -> str:
    """3X-UI client identifier. Internal user id + random suffix — never a Telegram id."""
    return f"u{user.id}s{server.id}-{secrets.token_hex(4)}"


async def create_access(
    db: AsyncSession,
    user: User,
    subscription: Subscription,
    server: VpnServer,
    traffic_limit_gb: int,
) -> VpnAccess:
    """Create a 3X-UI client on `server` for the subscription and persist the access row.

    Reuses an existing ACTIVE access for the same user+server (renewal case) by
    updating its expiry instead of creating a duplicate client.
    """
    existing = await db.scalar(
        select(VpnAccess).where(
            VpnAccess.user_id == user.id,
            VpnAccess.server_id == server.id,
            VpnAccess.status == AccessStatus.ACTIVE.value,
        )
    )
    client = panel_client(server)
    total_bytes = traffic_limit_gb * GB if traffic_limit_gb else 0

    if existing:
        await client.update_client(
            server.inbound_id,
            existing.uuid,
            existing.external_user_id,
            enable=True,
            total_bytes=total_bytes,
            expiry_time_ms=_expiry_ms(subscription.expires_at),
        )
        existing.subscription_id = subscription.id
        await db.flush()
        return existing

    client_uuid = str(uuidlib.uuid4())
    email = _client_email(user, server)
    await client.add_client(
        server.inbound_id,
        client_uuid,
        email,
        total_bytes=total_bytes,
        expiry_time_ms=_expiry_ms(subscription.expires_at),
        sub_id=secrets.token_hex(8),
    )
    access = VpnAccess(
        user_id=user.id,
        subscription_id=subscription.id,
        server_id=server.id,
        external_user_id=email,
        uuid=client_uuid,
        status=AccessStatus.ACTIVE.value,
    )
    db.add(access)
    await db.flush()
    logger.info("vpn access created: user=%s server=%s", user.id, server.id)
    return access


async def revoke_access(db: AsyncSession, access: VpnAccess, server: VpnServer) -> None:
    """Disable the client on the panel and mark the access row revoked.

    Panel errors are logged but do not prevent the local revocation — the client
    also has expiryTime set, so the panel cuts it off on its own.
    """
    try:
        client = panel_client(server)
        await client.update_client(
            server.inbound_id,
            access.uuid,
            access.external_user_id,
            enable=False,
            expiry_time_ms=_expiry_ms(datetime.now(timezone.utc)),
        )
    except XuiError as exc:
        logger.error("panel revoke failed (access=%s): %s", access.id, exc)
    access.status = AccessStatus.REVOKED.value
    access.revoked_at = datetime.now(timezone.utc)
    await db.flush()


async def renew_access(
    db: AsyncSession,
    access: VpnAccess,
    server: VpnServer,
    new_expiry: datetime,
    traffic_limit_gb: int,
) -> None:
    client = panel_client(server)
    await client.update_client(
        server.inbound_id,
        access.uuid,
        access.external_user_id,
        enable=True,
        total_bytes=traffic_limit_gb * GB if traffic_limit_gb else 0,
        expiry_time_ms=_expiry_ms(new_expiry),
    )
    access.status = AccessStatus.ACTIVE.value
    access.revoked_at = None
    await db.flush()


async def get_traffic(access: VpnAccess, server: VpnServer) -> dict | None:
    try:
        client = panel_client(server)
        return await client.get_client_traffic(access.external_user_id)
    except XuiError as exc:
        logger.warning("traffic fetch failed (access=%s): %s", access.id, exc)
        return None


def build_vless_link(access: VpnAccess, server: VpnServer) -> str:
    """VLESS + Reality connection URI understood by v2rayNG/Happ/Streisand/sing-box."""
    name = quote(f"{server.country} · {server.name}")
    return (
        f"vless://{access.uuid}@{server.host}:{server.port}"
        f"?type=tcp&security=reality&pbk={server.public_key}"
        f"&sid={server.short_id}&sni={server.sni}"
        f"&flow=xtls-rprx-vision&fp=chrome#{name}"
    )


async def get_config_links(db: AsyncSession, user: User) -> list[str]:
    """All active config links for the user across servers (for /sub/{token})."""
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
    return [build_vless_link(access, server) for access, server in rows]

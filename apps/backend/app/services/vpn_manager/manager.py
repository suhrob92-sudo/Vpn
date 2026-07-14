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


def _flow_for(server: VpnServer) -> str:
    """xtls-rprx-vision flow is valid ONLY for TCP+Reality. Any other transport
    (ws/grpc/xhttp) or TLS security must send an empty flow, else clients fail."""
    if server.transport == "tcp" and server.security == "reality":
        return "xtls-rprx-vision"
    return ""


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

    flow = _flow_for(server)
    if existing:
        await client.update_client(
            server.inbound_id,
            existing.uuid,
            existing.external_user_id,
            enable=True,
            total_bytes=total_bytes,
            expiry_time_ms=_expiry_ms(subscription.expires_at),
            flow=flow,
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
        flow=flow,
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
            flow=_flow_for(server),
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
        flow=_flow_for(server),
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
    """Build a VLESS URI for the server's transport + security combination.

    Understood by v2rayNG / Happ / Streisand / sing-box / NekoBox. Covers:
      • tcp + reality  → Wi-Fi / home (xtls-rprx-vision flow)
      • ws  + tls      → mobile LTE bypass, ideal behind Cloudflare CDN
      • grpc + reality|tls, xhttp + tls → additional mobile bypass transports
    """
    transport = server.transport or "tcp"
    security = server.security or "reality"
    params: dict[str, str] = {"type": transport, "security": security, "fp": "chrome"}

    # A uTLS "chrome" fingerprint advertises h2 in the TLS ALPN and overrides the
    # alpn field, so a CDN like Cloudflare negotiates HTTP/2 — over which the
    # WebSocket Upgrade fails. Drop the fingerprint for ws/xhttp so the client
    # offers only the http/1.1 alpn we set below and the WS handshake succeeds.
    if transport in ("ws", "xhttp"):
        params.pop("fp")

    if security == "reality":
        params["pbk"] = server.public_key
        params["sid"] = server.short_id
        params["sni"] = server.sni
    else:  # tls
        params["sni"] = server.sni
        # WebSocket (and xhttp) do an HTTP/1.1 Upgrade, which breaks if ALPN
        # negotiates h2 — so advertise only http/1.1 for those. Behind a CDN
        # like Cloudflare this is what keeps the WS handshake working; h2 stays
        # available for transports that can use it.
        params["alpn"] = "http/1.1" if transport in ("ws", "xhttp") else "h2,http/1.1"

    # xtls-rprx-vision flow is valid ONLY for tcp+reality.
    if transport == "tcp" and security == "reality":
        params["flow"] = "xtls-rprx-vision"

    if transport in ("ws", "xhttp"):
        params["path"] = server.network_path or "/"
        params["host"] = server.header_host or server.sni
    elif transport == "grpc":
        params["serviceName"] = server.network_path or ""
        params["mode"] = "gun"

    query = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in params.items() if v != "")
    name = quote(f"{server.country} · {server.name}")
    return f"vless://{access.uuid}@{server.host}:{server.port}?{query}#{name}"


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

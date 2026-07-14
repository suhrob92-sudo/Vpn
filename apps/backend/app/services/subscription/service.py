"""Subscription tokens and the universal subscription document.

Token security model:
- token = secrets.token_urlsafe(32); the URL never contains a Telegram ID;
- lookup / validation happens by SHA-256 hash (token_hash, unique);
- an encrypted copy (Fernet, key in env) is kept ONLY so the Connect screen can
  re-display the same stable URL later — a DB dump alone reveals no usable token.
  Lookup never touches the encrypted copy.
"""
import base64
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.security import generate_subscription_token, hash_token
from app.models import (
    Subscription,
    SubscriptionStatus,
    SubscriptionToken,
    TokenStatus,
    User,
    UserStatus,
)

logger = logging.getLogger(__name__)


async def ensure_token(db: AsyncSession, user: User) -> tuple[SubscriptionToken, str]:
    """Return the user's active token row and its raw value, creating one if needed."""
    row = await db.scalar(
        select(SubscriptionToken).where(
            SubscriptionToken.user_id == user.id,
            SubscriptionToken.status == TokenStatus.ACTIVE.value,
        )
    )
    if row is not None:
        return row, decrypt_secret(row.token_encrypted)

    raw = generate_subscription_token()
    row = SubscriptionToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        token_encrypted=encrypt_secret(raw),
        status=TokenStatus.ACTIVE.value,
    )
    db.add(row)
    await db.flush()
    return row, raw


async def get_raw_token(db: AsyncSession, user: User) -> str | None:
    row = await db.scalar(
        select(SubscriptionToken).where(
            SubscriptionToken.user_id == user.id,
            SubscriptionToken.status == TokenStatus.ACTIVE.value,
        )
    )
    return decrypt_secret(row.token_encrypted) if row else None


async def resolve_token(db: AsyncSession, raw_token: str) -> User | None:
    """Token → user, only if the token is active, the user is not suspended and
    an ACTIVE, unexpired subscription exists. Everything else → None (no VPN)."""
    row = await db.scalar(
        select(SubscriptionToken).where(
            SubscriptionToken.token_hash == hash_token(raw_token),
            SubscriptionToken.status == TokenStatus.ACTIVE.value,
        )
    )
    if row is None:
        return None
    user = await db.get(User, row.user_id)
    if user is None or user.status != UserStatus.ACTIVE.value:
        return None
    now = datetime.now(timezone.utc)
    sub = await db.scalar(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.expires_at > now,
        )
    )
    if sub is None:
        return None
    row.last_accessed_at = now
    await db.flush()
    return user


def subscription_url(raw_token: str) -> str:
    return f"{get_settings().sub_base_url.rstrip('/')}/sub/{raw_token}"


def build_subscription_body(links: list[str]) -> str:
    """Universal subscription format: base64 of newline-separated URIs.

    Readable by v2rayNG, Happ, Streisand, NekoBox and sing-box importers.
    """
    plain = "\n".join(links)
    return base64.b64encode(plain.encode()).decode()

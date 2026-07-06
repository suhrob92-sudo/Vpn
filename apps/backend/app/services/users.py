"""User upsert from Telegram data + referral tracking (MVP: tracking only)."""
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ReferralEvent, User


def _new_referral_code() -> str:
    return secrets.token_urlsafe(8)


async def upsert_from_telegram(
    db: AsyncSession, tg_user: dict, start_param: str | None = None
) -> User:
    """Create or refresh a user row from a Telegram user object
    (initData `user` field or aiogram message.from_user)."""
    user = await db.scalar(select(User).where(User.telegram_id == tg_user["id"]))
    if user is None:
        user = User(
            telegram_id=tg_user["id"],
            username=tg_user.get("username"),
            first_name=tg_user.get("first_name"),
            last_name=tg_user.get("last_name"),
            language_code=tg_user.get("language_code"),
            referral_code=_new_referral_code(),
        )
        db.add(user)
        await db.flush()
        if start_param:
            await _track_referral(db, user, start_param)
    else:
        user.username = tg_user.get("username")
        user.first_name = tg_user.get("first_name")
        user.last_name = tg_user.get("last_name")
        if tg_user.get("language_code"):
            user.language_code = tg_user.get("language_code")
        await db.flush()
    return user


async def _track_referral(db: AsyncSession, new_user: User, start_param: str) -> None:
    """Record the referral link (reward logic is out of MVP scope)."""
    inviter = await db.scalar(select(User).where(User.referral_code == start_param))
    if inviter is None or inviter.id == new_user.id:
        return
    new_user.referred_by = inviter.id
    db.add(ReferralEvent(inviter_id=inviter.id, invited_user_id=new_user.id))
    await db.flush()

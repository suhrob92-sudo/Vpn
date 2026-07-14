"""Telegram Mini App authentication."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.ratelimit import rate_limit
from app.core.security import InitDataError, create_token, validate_init_data
from app.schemas.common import ok
from app.schemas.user import TelegramAuthIn, UserOut
from app.services.users import upsert_from_telegram

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/telegram", dependencies=[Depends(rate_limit("auth", limit=20))])
async def telegram_auth(body: TelegramAuthIn, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    try:
        data = validate_init_data(body.init_data, settings.bot_token)
    except InitDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"initData invalid: {exc}"
        )
    tg_user = data.get("user")
    if not isinstance(tg_user, dict) or "id" not in tg_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no user in initData")

    user = await upsert_from_telegram(db, tg_user, data.get("start_param"))
    await db.commit()

    token = create_token(str(user.id), "user", settings.user_jwt_ttl)
    return ok(
        {
            "access_token": token,
            "user": UserOut.model_validate(user).model_dump(mode="json"),
        }
    )

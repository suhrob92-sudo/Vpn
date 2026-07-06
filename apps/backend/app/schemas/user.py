from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str | None
    referral_code: str
    status: str
    created_at: datetime


class UserPatch(BaseModel):
    language_code: str | None = None


class TelegramAuthIn(BaseModel):
    init_data: str


class TelegramAuthOut(BaseModel):
    access_token: str
    user: UserOut

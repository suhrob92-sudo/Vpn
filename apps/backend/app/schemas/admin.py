from decimal import Decimal

from pydantic import BaseModel


class AdminLoginIn(BaseModel):
    username: str
    password: str


class AdminGiftIn(BaseModel):
    plan_id: int


class AdminBalanceIn(BaseModel):
    amount: Decimal  # positive = top up, negative = deduct


class AdminTokensOut(BaseModel):
    access_token: str
    refresh_token: str


class AdminRefreshIn(BaseModel):
    refresh_token: str


class AdminUserPatch(BaseModel):
    status: str | None = None       # ACTIVE | SUSPENDED
    bonus_days: int | None = None   # extend active subscription by N days

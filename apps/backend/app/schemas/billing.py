from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    price: Decimal
    currency: str
    duration_days: int
    traffic_limit_gb: int
    device_hint: int
    discount_percent: int
    is_popular: bool
    is_active: bool
    sort_order: int


class PlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    price: Decimal = Field(gt=0)
    currency: str = "USDT"
    duration_days: int = Field(gt=0)
    traffic_limit_gb: int = Field(ge=0, default=0)
    device_hint: int = Field(ge=1, default=3)
    discount_percent: int = Field(ge=0, le=100, default=0)
    is_popular: bool = False
    is_active: bool = True
    sort_order: int = 0


class PlanPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    currency: str | None = None
    duration_days: int | None = Field(default=None, gt=0)
    traffic_limit_gb: int | None = Field(default=None, ge=0)
    device_hint: int | None = Field(default=None, ge=1)
    discount_percent: int | None = Field(default=None, ge=0, le=100)
    is_popular: bool | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    started_at: datetime
    expires_at: datetime
    plan: PlanOut


class PaymentCreateIn(BaseModel):
    plan_id: int
    provider: str | None = None  # None → backend default (default_payment_provider)


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    amount: Decimal
    currency: str
    status: str
    invoice_url: str | None
    created_at: datetime
    paid_at: datetime | None

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class Plan(TimestampMixin, Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USDT", nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    traffic_limit_gb: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0 = unlimited
    device_hint: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # informational only
    discount_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_popular: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=SubscriptionStatus.ACTIVE.value, nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    plan: Mapped[Plan] = relationship(lazy="joined")


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)  # cryptobot | stars
    # Idempotency anchor: e.g. "cryptobot:<invoice_id>". Unique -> a replayed
    # webhook can never activate twice.
    provider_payment_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=PaymentStatus.PENDING.value, nullable=False, index=True
    )
    invoice_url: Mapped[str | None] = mapped_column(Text)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    plan: Mapped[Plan] = relationship(lazy="joined")

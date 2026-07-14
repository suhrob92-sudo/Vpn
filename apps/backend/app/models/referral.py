from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ReferralEvent(TimestampMixin, Base):
    """Referral tracking only in MVP — reward logic comes later."""

    __tablename__ = "referral_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    inviter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    invited_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="TRACKED", nullable=False)

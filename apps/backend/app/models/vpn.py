import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ServerStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    MAINTENANCE = "MAINTENANCE"
    OFFLINE = "OFFLINE"


class AccessStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class TokenStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class VpnServer(TimestampMixin, Base):
    __tablename__ = "vpn_servers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    country: Mapped[str] = mapped_column(String(64), nullable=False)  # ISO code or name
    city: Mapped[str | None] = mapped_column(String(128))
    panel_url: Mapped[str] = mapped_column(Text, nullable=False)  # incl. web base path
    panel_user: Mapped[str] = mapped_column(String(128), nullable=False)
    panel_pass_encrypted: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet
    inbound_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # Connection parameters for building client links (VLESS + Reality)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=443, nullable=False)
    public_key: Mapped[str] = mapped_column(String(255), nullable=False)
    short_id: Mapped[str] = mapped_column(String(64), nullable=False)
    sni: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=ServerStatus.ONLINE.value, nullable=False
    )


class VpnAccess(TimestampMixin, Base):
    __tablename__ = "vpn_access"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id"), index=True, nullable=False
    )
    server_id: Mapped[int] = mapped_column(ForeignKey("vpn_servers.id"), nullable=False)
    # 3X-UI client identifier (the client "email" field) — internal, not a Telegram id
    external_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    uuid: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=AccessStatus.ACTIVE.value, nullable=False, index=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SubscriptionToken(TimestampMixin, Base):
    __tablename__ = "subscription_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # Fernet-encrypted raw token, used ONLY to re-display the stable subscription
    # URL in the Connect screen. Lookup/validation always goes through token_hash.
    token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=TokenStatus.ACTIVE.value, nullable=False
    )
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

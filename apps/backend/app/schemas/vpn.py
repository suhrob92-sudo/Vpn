from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ServerPublicOut(BaseModel):
    """What regular users see — no panel details."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country: str
    city: str | None
    status: str


class ServerAdminOut(ServerPublicOut):
    panel_url: str
    panel_user: str
    inbound_id: int
    host: str
    port: int
    transport: str
    security: str
    public_key: str
    short_id: str
    sni: str
    network_path: str
    header_host: str
    created_at: datetime


class ServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    country: str
    city: str | None = None
    panel_url: str
    panel_user: str
    panel_pass: str  # encrypted before storage
    inbound_id: int
    host: str
    port: int = 443
    transport: str = "tcp"       # tcp | ws | grpc | xhttp
    security: str = "reality"    # reality | tls
    public_key: str = ""         # Reality only
    short_id: str = ""           # Reality only
    sni: str
    network_path: str = ""       # ws/xhttp path or grpc serviceName
    header_host: str = ""        # Host header / Cloudflare domain
    status: str = "ONLINE"


class ServerPatch(BaseModel):
    name: str | None = None
    country: str | None = None
    city: str | None = None
    panel_url: str | None = None
    panel_user: str | None = None
    panel_pass: str | None = None
    inbound_id: int | None = None
    host: str | None = None
    port: int | None = None
    transport: str | None = None
    security: str | None = None
    public_key: str | None = None
    short_id: str | None = None
    sni: str | None = None
    network_path: str | None = None
    header_host: str | None = None
    status: str | None = None


class ConnectInfoOut(BaseModel):
    subscription_url: str
    deep_links: dict[str, str]
    traffic: dict | None = None

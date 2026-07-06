"""Application settings, loaded from environment / .env."""
from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    domain: str = "localhost"
    api_base_url: str = "http://localhost:8000"
    sub_base_url: str = "http://localhost:8000"
    miniapp_url: str = "http://localhost:3000"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "vpn"
    postgres_user: str = "vpn"
    postgres_password: str = "vpn"
    database_url_override: str = ""  # tests / special setups

    redis_url: str = "redis://localhost:6379/0"

    bot_token: str = ""
    admin_chat_id: int = 0

    cryptobot_api_token: str = ""
    cryptobot_api_url: str = "https://pay.crypt.bot/api"
    cryptobot_asset: str = "USDT"
    cryptobot_webhook_secret: str = "webhook-secret"

    jwt_secret: str = "dev-secret-change-me"
    encryption_key: str = ""
    admin_bootstrap_username: str = "admin"
    admin_bootstrap_password: str = ""

    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # auth lifetimes (seconds)
    user_jwt_ttl: int = 24 * 3600
    admin_access_ttl: int = 15 * 60
    admin_refresh_ttl: int = 7 * 24 * 3600
    init_data_max_age: int = 3600

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()

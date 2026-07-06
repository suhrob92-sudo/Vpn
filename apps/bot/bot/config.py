from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = ""
    # Backend reachable inside the compose network; never through the public proxy.
    internal_api_url: str = "http://backend:8000"
    miniapp_url: str = "http://localhost:3000"
    jwt_secret: str = "dev-secret-change-me"  # shared HMAC secret for internal API
    admin_chat_id: int = 0
    support_contact: str = "@your_support"


@lru_cache
def get_settings() -> BotSettings:
    return BotSettings()

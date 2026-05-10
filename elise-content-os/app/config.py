from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    tz: str = Field(default="Asia/Dubai", validation_alias="TZ")

    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-5.4-mini"
    openai_fallback_model: str = "gpt-5.4-mini"

    database_url: str = "sqlite:///./local.db"
    database_url_direct: Optional[str] = None

    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_webhook_secret: str = "change-me"

    app_base_url: str = "http://localhost:8000"
    internal_trigger_token: str = "change-me"

    story_daily_target: int = 4

    @property
    def app_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    @property
    def workspace_root(self) -> Path:
        return self.app_root.parent

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    def normalized_database_url(self, direct: bool = False) -> str:
        url = self.database_url_direct if direct and self.database_url_direct else self.database_url
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url.removeprefix("postgres://")
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url.removeprefix("postgresql://")
        return url

    def require_openai_key(self) -> str:
        if not self.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for non-dry-run content generation.")
        return self.openai_api_key

    def require_telegram(self) -> tuple[str, str]:
        if not self.telegram_bot_token or not self.telegram_chat_id:
            raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required.")
        return self.telegram_bot_token, self.telegram_chat_id


@lru_cache
def get_settings() -> Settings:
    return Settings()

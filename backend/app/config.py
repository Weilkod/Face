from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="dev")
    log_level: str = Field(default="INFO")

    database_url: str = Field(
        default=f"sqlite+aiosqlite:///{(PROJECT_ROOT / 'data' / 'facemetrics.db').as_posix()}"
    )

    anthropic_api_key: str = Field(default="")
    claude_model_vision: str = Field(default="claude-opus-4-6")
    claude_model_text: str = Field(default="claude-sonnet-4-6")

    scheduler_enabled: bool = Field(default=True)
    scheduler_timezone: str = Field(default="Asia/Seoul")
    crawl_hour: int = Field(default=8)
    analyze_hour: int = Field(default=10)
    analyze_minute: int = Field(default=30)
    publish_hour: int = Field(default=11)

    frontend_origin: str = Field(default="http://localhost:3000")

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

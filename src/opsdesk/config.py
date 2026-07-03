from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "OpsDesk Reviewer Replay"
    app_env: str = "development"
    database_url: str = "sqlite:///./opsdesk.db"
    redis_url: str = "redis://localhost:6379/0"
    sla_minutes_high: int = Field(default=60, ge=1)
    sla_minutes_normal: int = Field(default=240, ge=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""Pydantic Settings loaded from environment / Azure Key Vault."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and a local .env file."""

    environment: str = "local"
    debug: bool = False
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://rentflow:rentflow@db:5432/rentflow"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    backend_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    azure_storage_connection_string: str | None = None
    azure_storage_container: str = "rentflow-documents"
    azure_key_vault_url: str | None = None
    applicationinsights_connection_string: str | None = None
    azure_communication_connection_string: str | None = None
    notification_from_email: str | None = None

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[1] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value)]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

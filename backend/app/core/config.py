"""Pydantic Settings loaded from environment / Azure Key Vault.

Locally everything comes from environment variables and ``backend/.env``. In
Azure, ``AZURE_KEY_VAULT_URL`` is set and the secrets in ``KEY_VAULT_SECRETS``
are read from Key Vault with the app's managed identity. An explicit environment
variable still wins over Key Vault, which is useful for emergency overrides.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

logger = logging.getLogger(__name__)

# Settings field -> Key Vault secret name. Key Vault names allow only letters,
# digits and dashes, so the mapping is explicit rather than derived.
KEY_VAULT_SECRETS: dict[str, str] = {
    "secret_key": "secret-key",
    "azure_communication_connection_string": "azure-communication-connection-string",
}

_DEPLOYED_ENVIRONMENTS = frozenset({"staging", "production"})
_INSECURE_SECRET_KEY = "change-me"  # noqa: S105 - the placeholder we refuse to deploy with


class KeyVaultSettingsSource(PydanticBaseSettingsSource):
    """Read the secrets in ``KEY_VAULT_SECRETS`` from Azure Key Vault.

    Only runs when ``azure_key_vault_url`` has been resolved by a higher-priority
    source (normally the ``AZURE_KEY_VAULT_URL`` env var set by Bicep). Fields
    already set by those sources are not fetched. A secret that does not exist
    in the vault is skipped so optional integrations can stay unset.
    """

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        # Values are loaded in bulk by __call__.
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        state = self.current_state
        vault_url = state.get("azure_key_vault_url")
        if not vault_url:
            return {}

        from azure.core.exceptions import ResourceNotFoundError
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        client = SecretClient(
            vault_url=vault_url,
            credential=DefaultAzureCredential(
                managed_identity_client_id=state.get("azure_client_id")
            ),
        )
        values: dict[str, Any] = {}
        for field_name, secret_name in KEY_VAULT_SECRETS.items():
            if state.get(field_name) not in (None, ""):
                continue
            try:
                values[field_name] = client.get_secret(secret_name).value
            except ResourceNotFoundError:
                logger.warning(
                    "Key Vault secret not found",
                    extra={"context": {"secret": secret_name}},
                )
        return values


class Settings(BaseSettings):
    """Application settings loaded from environment variables and a local .env file."""

    environment: str = "local"
    debug: bool = False
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://rentflow:rentflow@db:5432/rentflow"
    # Azure: sign in to PostgreSQL with a managed-identity Entra token instead of
    # a password. DATABASE_URL then names the identity as the user, with no password.
    database_entra_auth: bool = False
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    backend_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Client ID of the user-assigned managed identity the app runs as in Azure.
    # Unset locally, where DefaultAzureCredential falls back to developer logins.
    azure_client_id: str | None = None

    # Blob Storage: connection string locally (Azurite), account URL + managed
    # identity in Azure. Shared-key access is disabled on the Azure accounts.
    azure_storage_connection_string: str | None = None
    azure_storage_account_url: str | None = None
    azure_storage_container: str = "rentflow-documents"
    max_upload_bytes: int = 10 * 1024 * 1024
    azure_key_vault_url: str | None = None
    applicationinsights_connection_string: str | None = None
    azure_communication_connection_string: str | None = None
    notification_from_email: str | None = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Earlier sources win: explicit init/env/.env values override Key Vault.
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            KeyVaultSettingsSource(settings_cls),
            file_secret_settings,
        )

    @model_validator(mode="after")
    def require_real_secret_key_when_deployed(self) -> Settings:
        if self.environment in _DEPLOYED_ENVIRONMENTS and self.secret_key in (
            "",
            _INSECURE_SECRET_KEY,
        ):
            raise ValueError(
                f"SECRET_KEY must be set (Key Vault secret 'secret-key') in {self.environment}"
            )
        return self

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
            if value.lstrip().startswith("["):
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value)]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

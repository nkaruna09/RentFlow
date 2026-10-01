"""Tests for loading settings from Azure Key Vault."""

from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import ResourceNotFoundError
from pydantic import ValidationError

from app.core.config import Settings

VAULT_URL = "https://kv-rentflow-staging.vault.azure.net/"


def _secret_client(secrets: dict[str, str]) -> MagicMock:
    def get_secret(name: str) -> MagicMock:
        if name not in secrets:
            raise ResourceNotFoundError(f"{name} not found")
        return MagicMock(value=secrets[name])

    client = MagicMock()
    client.get_secret.side_effect = get_secret
    return client


@pytest.fixture
def no_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate from backend/.env and any SECRET_KEY in the shell (e.g. CI)."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for name in ("SECRET_KEY", "AZURE_KEY_VAULT_URL", "AZURE_CLIENT_ID", "ENVIRONMENT"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.usefixtures("no_dotenv")
def test_key_vault_is_not_contacted_without_a_vault_url() -> None:
    with patch("azure.keyvault.secrets.SecretClient") as client_cls:
        settings = Settings()
    client_cls.assert_not_called()
    assert settings.secret_key == "change-me"


@pytest.mark.usefixtures("no_dotenv")
def test_secrets_load_from_key_vault_with_the_managed_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_KEY_VAULT_URL", VAULT_URL)
    monkeypatch.setenv("AZURE_CLIENT_ID", "11111111-1111-1111-1111-111111111111")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    client = _secret_client({"secret-key": "from-key-vault"})

    with (
        patch("azure.keyvault.secrets.SecretClient", return_value=client) as client_cls,
        patch("azure.identity.DefaultAzureCredential") as credential_cls,
    ):
        settings = Settings()

    assert settings.secret_key == "from-key-vault"
    # Optional secrets that are absent from the vault stay unset.
    assert settings.azure_communication_connection_string is None
    assert client_cls.call_args.kwargs["vault_url"] == VAULT_URL
    credential_cls.assert_called_once_with(
        managed_identity_client_id="11111111-1111-1111-1111-111111111111"
    )


@pytest.mark.usefixtures("no_dotenv")
def test_explicit_environment_variables_override_key_vault(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_KEY_VAULT_URL", VAULT_URL)
    monkeypatch.setenv("SECRET_KEY", "explicit-override")
    client = _secret_client({"secret-key": "from-key-vault"})

    with (
        patch("azure.keyvault.secrets.SecretClient", return_value=client),
        patch("azure.identity.DefaultAzureCredential"),
    ):
        settings = Settings()

    assert settings.secret_key == "explicit-override"
    requested = [call.args[0] for call in client.get_secret.call_args_list]
    assert "secret-key" not in requested


@pytest.mark.usefixtures("no_dotenv")
@pytest.mark.parametrize("environment", ["staging", "production"])
def test_deployed_environments_refuse_the_placeholder_secret_key(environment: str) -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY must be set"):
        Settings(environment=environment)

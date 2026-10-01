"""Shared Azure credential for managed-identity access to Azure services."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from app.core.config import get_settings

if TYPE_CHECKING:
    from azure.identity import DefaultAzureCredential


@lru_cache(maxsize=1)
def get_azure_credential() -> DefaultAzureCredential:
    """Return one process-wide credential so tokens are cached and reused.

    In Container Apps this resolves to the app's user-assigned managed identity
    (``AZURE_CLIENT_ID``); on a developer machine it falls back to ``az login``.
    """
    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential(managed_identity_client_id=get_settings().azure_client_id)


__all__ = ["get_azure_credential"]

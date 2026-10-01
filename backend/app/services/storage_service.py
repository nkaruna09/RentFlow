"""Azure Blob Storage uploads for leases and receipts.

This module only moves bytes. Access control and the ``documents`` metadata
rows live in ``document_service``. Files are proxied through the API rather
than uploaded directly with SAS tokens (see docs/architecture.md §7).

The sync Azure SDK client runs in a worker thread; files are capped at
``MAX_UPLOAD_BYTES`` so holding one in memory is fine.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from functools import lru_cache
from urllib.parse import unquote, urlparse

from azure.storage.blob import BlobServiceClient, ContainerClient, ContentSettings

from app.core.azure import get_azure_credential
from app.core.config import get_settings
from app.core.exceptions import RentFlowError

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


class StorageNotConfiguredError(RentFlowError):
    def __init__(self) -> None:
        super().__init__(
            detail="Document storage is not configured",
            status_code=503,
            code="storage_not_configured",
        )


@lru_cache(maxsize=1)
def _container_client() -> ContainerClient:
    settings = get_settings()
    if settings.azure_storage_connection_string:
        # Local development against Azurite: create the container on first use.
        service = BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
        container = service.get_container_client(settings.azure_storage_container)
        if not container.exists():
            container.create_container()
        return container
    if settings.azure_storage_account_url:
        # Azure: managed identity only. The container is provisioned by Bicep.
        service = BlobServiceClient(
            settings.azure_storage_account_url, credential=get_azure_credential()
        )
        return service.get_container_client(settings.azure_storage_container)
    raise StorageNotConfiguredError()


def safe_filename(filename: str) -> str:
    """Reduce a user-supplied filename to a safe blob path segment."""
    cleaned = _UNSAFE_FILENAME_CHARS.sub("_", filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1])
    cleaned = cleaned.strip("._") or "file"
    return cleaned[:120]


def blob_name_for(
    owner_type: str, owner_id: uuid.UUID, document_id: uuid.UUID, filename: str
) -> str:
    return f"{owner_type}/{owner_id}/{document_id}/{safe_filename(filename)}"


def blob_name_from_url(blob_url: str) -> str:
    """Recover the blob name from a stored blob URL (path after the container)."""
    container = get_settings().azure_storage_container
    path = unquote(urlparse(blob_url).path).lstrip("/")
    marker = f"{container}/"
    if marker not in path:
        raise ValueError(f"Blob URL is not in the {container!r} container")
    return path.split(marker, 1)[1]


def _upload(blob_name: str, data: bytes, content_type: str) -> str:
    blob = _container_client().get_blob_client(blob_name)
    blob.upload_blob(
        data,
        overwrite=False,
        content_settings=ContentSettings(content_type=content_type),
    )
    return str(blob.url)


def _download(blob_name: str) -> bytes:
    return bytes(_container_client().get_blob_client(blob_name).download_blob().readall())


def _delete(blob_name: str) -> None:
    _container_client().get_blob_client(blob_name).delete_blob(delete_snapshots="include")


async def upload(blob_name: str, data: bytes, content_type: str) -> str:
    """Upload a new blob and return its URL. Never overwrites an existing blob."""
    return await asyncio.to_thread(_upload, blob_name, data, content_type)


async def download(blob_name: str) -> bytes:
    return await asyncio.to_thread(_download, blob_name)


async def delete(blob_name: str) -> None:
    await asyncio.to_thread(_delete, blob_name)


__all__ = [
    "StorageNotConfiguredError",
    "blob_name_for",
    "blob_name_from_url",
    "delete",
    "download",
    "safe_filename",
    "upload",
]

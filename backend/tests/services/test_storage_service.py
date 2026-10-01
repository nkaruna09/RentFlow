"""Tests for blob naming and configuration in storage_service."""

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from app.core.config import Settings
from app.services import storage_service

OWNER_ID = UUID("11111111-1111-1111-1111-111111111111")
DOCUMENT_ID = UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture(autouse=True)
def _clear_client_cache():
    storage_service._container_client.cache_clear()
    yield
    storage_service._container_client.cache_clear()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("lease.pdf", "lease.pdf"),
        ("../../etc/passwd", "passwd"),
        ("C:\\Users\\me\\Receipt March.png", "Receipt_March.png"),
        ("...", "file"),
        ("été 2026.pdf", "t_2026.pdf"),
    ],
)
def test_safe_filename_strips_paths_and_unsafe_characters(raw: str, expected: str) -> None:
    assert storage_service.safe_filename(raw) == expected


def test_blob_name_round_trips_through_the_blob_url() -> None:
    name = storage_service.blob_name_for("lease", OWNER_ID, DOCUMENT_ID, "Signed lease.pdf")
    assert name == f"lease/{OWNER_ID}/{DOCUMENT_ID}/Signed_lease.pdf"

    url = f"https://strentflowstaging.blob.core.windows.net/rentflow-documents/{name}"
    assert storage_service.blob_name_from_url(url) == name


def test_blob_name_from_url_rejects_other_containers() -> None:
    with pytest.raises(ValueError):
        storage_service.blob_name_from_url("https://acct.blob.core.windows.net/other/x.pdf")


def test_unconfigured_storage_raises_503() -> None:
    with (
        patch.object(storage_service, "get_settings", return_value=Settings()),
        pytest.raises(storage_service.StorageNotConfiguredError) as error,
    ):
        storage_service._container_client()
    assert error.value.status_code == 503


def test_azure_storage_uses_the_managed_identity_credential() -> None:
    settings = Settings(azure_storage_account_url="https://strentflowstaging.blob.core.windows.net")
    credential = object()
    with (
        patch.object(storage_service, "get_settings", return_value=settings),
        patch.object(storage_service, "get_azure_credential", return_value=credential),
        patch.object(storage_service, "BlobServiceClient") as service_cls,
    ):
        storage_service._container_client()

    service_cls.assert_called_once_with(settings.azure_storage_account_url, credential=credential)
    service_cls.return_value.get_container_client.assert_called_once_with("rentflow-documents")


async def test_upload_never_overwrites_and_returns_the_blob_url() -> None:
    container = MagicMock()
    blob = container.get_blob_client.return_value
    blob.url = "https://acct.blob.core.windows.net/rentflow-documents/a/b.pdf"
    with patch.object(storage_service, "_container_client", return_value=container):
        url = await storage_service.upload("a/b.pdf", b"%PDF", "application/pdf")

    assert url == blob.url
    kwargs = blob.upload_blob.call_args.kwargs
    assert kwargs["overwrite"] is False
    assert kwargs["content_settings"].content_type == "application/pdf"

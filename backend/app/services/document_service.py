"""Attach files to leases, payments and maintenance requests.

Access follows the owning record: if the caller cannot see the lease, payment
or maintenance request, the document does not exist for them either.

| owner_type          | read                           | upload                  |
| ------------------- | ------------------------------ | ----------------------- |
| lease               | owner landlord/manager, tenant | owner landlord/manager  |
| payment (receipts)  | owner landlord/manager         | owner landlord/manager  |
| maintenance_request | anyone who can see the request | anyone who can see it   |
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.models.document import Document, DocumentOwnerType
from app.models.user import User, UserRole
from app.repositories import document as document_repository
from app.repositories import lease as lease_repository
from app.repositories import maintenance as maintenance_repository
from app.repositories import payment as payment_repository
from app.services import storage_service

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = frozenset({"application/pdf", "image/jpeg", "image/png", "image/webp"})
_MANAGER_ROLES = frozenset({UserRole.LANDLORD, UserRole.MANAGER})


async def _ensure_owner_access(
    db: AsyncSession,
    current_user: User,
    owner_type: DocumentOwnerType,
    owner_id: uuid.UUID,
    *,
    write: bool,
) -> None:
    is_manager = current_user.role in _MANAGER_ROLES
    if owner_type == DocumentOwnerType.LEASE:
        lease = await lease_repository.get_visible(db, owner_id, current_user.id, current_user.role)
        if lease is None:
            raise NotFoundError("Lease not found")
        if write and not is_manager:
            raise AuthorizationError("Only landlords and managers can upload lease documents")
    elif owner_type == DocumentOwnerType.PAYMENT:
        payment = (
            await payment_repository.get_payment_for_owner(db, owner_id, current_user.id)
            if is_manager
            else None
        )
        if payment is None:
            raise NotFoundError("Payment not found")
    else:
        request = await maintenance_repository.get_visible(
            db, owner_id, current_user.id, current_user.role
        )
        if request is None:
            raise NotFoundError("Maintenance request not found")


async def upload_document(
    db: AsyncSession,
    current_user: User,
    *,
    owner_type: DocumentOwnerType,
    owner_id: uuid.UUID,
    filename: str,
    content_type: str,
    data: bytes,
) -> Document:
    """Validate, store the blob, then record its metadata."""
    await _ensure_owner_access(db, current_user, owner_type, owner_id, write=True)
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError("Only PDF, JPEG, PNG or WebP files can be uploaded")
    if not data:
        raise ValidationError("The uploaded file is empty")
    max_bytes = get_settings().max_upload_bytes
    if len(data) > max_bytes:
        raise ValidationError(f"Files must be at most {max_bytes // (1024 * 1024)} MB")

    document_id = uuid.uuid4()
    blob_name = storage_service.blob_name_for(owner_type.value, owner_id, document_id, filename)
    blob_url = await storage_service.upload(blob_name, data, content_type)
    document = Document(
        id=document_id,
        owner_type=owner_type,
        owner_id=owner_id,
        blob_url=blob_url,
        filename=filename,
        content_type=content_type,
        size_bytes=len(data),
        uploaded_by=current_user.id,
    )
    try:
        return await document_repository.create(db, document)
    except Exception:
        # Don't leave an orphaned blob behind when the metadata insert fails.
        try:
            await storage_service.delete(blob_name)
        except Exception:
            logger.warning(
                "Failed to delete orphaned document blob",
                extra={"context": {"blob_name": blob_name}},
            )
        raise


async def list_documents(
    db: AsyncSession,
    current_user: User,
    *,
    owner_type: DocumentOwnerType,
    owner_id: uuid.UUID,
) -> list[Document]:
    await _ensure_owner_access(db, current_user, owner_type, owner_id, write=False)
    return await document_repository.list_for_owner(db, owner_type, owner_id)


async def get_document_content(
    db: AsyncSession, current_user: User, document_id: uuid.UUID
) -> tuple[Document, bytes]:
    document = await document_repository.get(db, document_id)
    if document is None:
        raise NotFoundError("Document not found")
    try:
        await _ensure_owner_access(
            db, current_user, document.owner_type, document.owner_id, write=False
        )
    except NotFoundError as exc:
        # Same 404 whether the document or its owner is hidden, so IDs don't leak.
        raise NotFoundError("Document not found") from exc
    data = await storage_service.download(storage_service.blob_name_from_url(document.blob_url))
    return document, data


__all__ = [
    "ALLOWED_CONTENT_TYPES",
    "get_document_content",
    "list_documents",
    "upload_document",
]

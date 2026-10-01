"""Document upload, listing and download (proxied through the API)."""

from __future__ import annotations

import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.db.session import get_db
from app.models.document import DocumentOwnerType
from app.models.user import User, UserRole
from app.schemas.document import DocumentList, DocumentRead
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])
document_users = require_role(UserRole.LANDLORD, UserRole.MANAGER, UserRole.TENANT)
CurrentDocumentUser = Annotated[User, Depends(document_users)]


@router.get("", response_model=DocumentList)
async def list_documents(
    owner_type: DocumentOwnerType,
    owner_id: uuid.UUID,
    current_user: CurrentDocumentUser,
    db: AsyncSession = Depends(get_db),
) -> DocumentList:
    documents = await document_service.list_documents(
        db, current_user, owner_type=owner_type, owner_id=owner_id
    )
    return DocumentList(
        items=[DocumentRead.model_validate(document) for document in documents],
        total=len(documents),
    )


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    current_user: CurrentDocumentUser,
    owner_type: Annotated[DocumentOwnerType, Form()],
    owner_id: Annotated[uuid.UUID, Form()],
    file: Annotated[UploadFile, File()],
    db: AsyncSession = Depends(get_db),
) -> DocumentRead:
    if not file.filename:
        raise ValidationError("The uploaded file needs a filename")
    # Read one byte past the limit so the service can reject oversized files
    # without buffering an arbitrarily large body.
    data = await file.read(get_settings().max_upload_bytes + 1)
    document = await document_service.upload_document(
        db,
        current_user,
        owner_type=owner_type,
        owner_id=owner_id,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        data=data,
    )
    return DocumentRead.model_validate(document)


@router.get("/{document_id}/content")
async def download_document(
    document_id: uuid.UUID,
    current_user: CurrentDocumentUser,
    db: AsyncSession = Depends(get_db),
) -> Response:
    document, data = await document_service.get_document_content(db, current_user, document_id)
    disposition = "attachment; filename*=UTF-8''" + quote(document.filename)
    return Response(
        content=data,
        media_type=document.content_type,
        headers={
            "Content-Disposition": disposition,
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )

"""Pydantic schemas for stored documents."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentOwnerType


class DocumentRead(BaseModel):
    """Document metadata returned by the API. The blob URL is not exposed:
    storage is private and downloads are proxied through the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_type: DocumentOwnerType
    owner_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    uploaded_by: uuid.UUID
    created_at: datetime


class DocumentList(BaseModel):
    items: list[DocumentRead]
    total: int


__all__ = ["DocumentList", "DocumentOwnerType", "DocumentRead"]

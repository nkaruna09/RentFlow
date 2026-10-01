"""Persistence queries for document metadata."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentOwnerType


async def list_for_owner(
    db: AsyncSession, owner_type: DocumentOwnerType, owner_id: uuid.UUID
) -> list[Document]:
    result = await db.scalars(
        select(Document)
        .where(Document.owner_type == owner_type, Document.owner_id == owner_id)
        .order_by(Document.created_at.desc())
    )
    return list(result.all())


async def get(db: AsyncSession, document_id: uuid.UUID) -> Document | None:
    return await db.get(Document, document_id)


async def create(db: AsyncSession, document: Document) -> Document:
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


__all__ = ["create", "get", "list_for_owner"]

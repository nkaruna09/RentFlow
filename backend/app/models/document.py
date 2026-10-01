"""Document metadata table (blobs live in Azure Blob Storage)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentOwnerType(str, enum.Enum):
    """Records a document can be attached to (the polymorphic ``owner_type``)."""

    LEASE = "lease"
    PAYMENT = "payment"
    MAINTENANCE_REQUEST = "maintenance_request"


class Document(Base):
    """Metadata for a file stored in the ``rentflow-documents`` blob container.

    ``owner_type``/``owner_id`` is a polymorphic link, so there is no foreign key
    on ``owner_id``; the document service checks the owner exists and is visible
    to the caller before a row is written.
    """

    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_owner", "owner_type", "owner_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_type: Mapped[DocumentOwnerType] = mapped_column(
        Enum(
            DocumentOwnerType,
            name="document_owner_type",
            values_callable=lambda types: [owner_type.value for owner_type in types],
        ),
        nullable=False,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    blob_url: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


__all__ = ["Document", "DocumentOwnerType"]

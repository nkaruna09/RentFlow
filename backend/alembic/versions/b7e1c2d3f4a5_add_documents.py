"""add documents

Revision ID: b7e1c2d3f4a5
Revises: 740aa36a8c4d
Create Date: 2026-09-30 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "b7e1c2d3f4a5"
down_revision = "740aa36a8c4d"
branch_labels = None
depends_on = None

document_owner_type = postgresql.ENUM(
    "lease",
    "payment",
    "maintenance_request",
    name="document_owner_type",
    create_type=False,
)


def upgrade() -> None:
    """Create the documents metadata table."""
    document_owner_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_type", document_owner_type, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("blob_url", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_owner", "documents", ["owner_type", "owner_id"])


def downgrade() -> None:
    """Drop the documents table. Blobs in storage are not touched."""
    op.drop_index("ix_documents_owner", table_name="documents")
    op.drop_table("documents")
    document_owner_type.drop(op.get_bind(), checkfirst=True)

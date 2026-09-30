"""add maintenance requests and comments

Revision ID: 740aa36a8c4d
Revises: d3e4f5a6b7c8
Create Date: 2026-09-27 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "740aa36a8c4d"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None

maintenance_priority = postgresql.ENUM(
    "low",
    "medium",
    "high",
    "emergency",
    name="maintenance_priority",
    create_type=False,
)
maintenance_status = postgresql.ENUM(
    "open",
    "assigned",
    "in_progress",
    "resolved",
    "closed",
    name="maintenance_status",
    create_type=False,
)


def upgrade() -> None:
    """Create maintenance requests, comments, and their enum types."""
    bind = op.get_bind()
    maintenance_priority.create(bind, checkfirst=True)
    maintenance_status.create(bind, checkfirst=True)

    op.create_table(
        "maintenance_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reported_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", maintenance_priority, nullable=False),
        sa.Column("status", maintenance_status, server_default="open", nullable=False),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reported_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_maintenance_requests_unit_id_status",
        "maintenance_requests",
        ["unit_id", "status"],
    )

    op.create_table(
        "maintenance_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["request_id"], ["maintenance_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_maintenance_comments_request_id", "maintenance_comments", ["request_id"])


def downgrade() -> None:
    """Drop maintenance tables and their enum types."""
    op.drop_index("ix_maintenance_comments_request_id", table_name="maintenance_comments")
    op.drop_table("maintenance_comments")
    op.drop_index("ix_maintenance_requests_unit_id_status", table_name="maintenance_requests")
    op.drop_table("maintenance_requests")
    maintenance_status.drop(op.get_bind(), checkfirst=True)
    maintenance_priority.drop(op.get_bind(), checkfirst=True)

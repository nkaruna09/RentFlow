"""add invoice late fee amount

Revision ID: c2d3e4f5a6b7
Revises: b7c8d9e0f1a2
Create Date: 2026-09-26 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "c2d3e4f5a6b7"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Store the applied fee as both an audit value and idempotency marker."""
    op.add_column("invoices", sa.Column("late_fee_amount", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    """Remove the invoice late-fee marker."""
    op.drop_column("invoices", "late_fee_amount")

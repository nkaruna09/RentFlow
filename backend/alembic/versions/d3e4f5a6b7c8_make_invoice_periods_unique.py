"""make invoice periods unique

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-09-26 00:00:00.000000

"""

from __future__ import annotations

from alembic import op

revision = "d3e4f5a6b7c8"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Prevent duplicate invoices for the same lease billing period."""
    op.create_unique_constraint(
        "uq_invoices_lease_period",
        "invoices",
        ["lease_id", "period_start", "period_end"],
    )


def downgrade() -> None:
    """Remove invoice-period uniqueness enforcement."""
    op.drop_constraint("uq_invoices_lease_period", "invoices", type_="unique")

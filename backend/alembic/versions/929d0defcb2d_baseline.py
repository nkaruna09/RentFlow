"""baseline

Revision ID: 929d0defcb2d
Revises:
Create Date: 2026-08-08 00:00:00.000000

"""

from __future__ import annotations

revision = "929d0defcb2d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Baseline no-op migration for the current ORM metadata."""
    pass


def downgrade() -> None:
    """No-op downgrade for the baseline revision."""
    pass

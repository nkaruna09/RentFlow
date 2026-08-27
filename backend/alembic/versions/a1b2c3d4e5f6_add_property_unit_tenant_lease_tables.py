"""add property, unit, tenant, and lease tables

Revision ID: a1b2c3d4e5f6
Revises: ff9cd843f3aa
Create Date: 2026-08-26 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "ff9cd843f3aa"
branch_labels = None
depends_on = None

property_type = postgresql.ENUM(
    "single_family", "multi_family", "condo", "commercial", name="property_type", create_type=False
)
unit_status = postgresql.ENUM(
    "vacant",
    "occupied",
    "unavailable",
    name="unit_status",
    create_type=False,
)
lease_status = postgresql.ENUM(
    "draft",
    "active",
    "expired",
    "terminated",
    name="lease_status",
    create_type=False,
)


def upgrade() -> None:
    """Create the core rental domain tables and the active-lease exclusion constraint."""
    bind = op.get_bind()
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    property_type.create(bind, checkfirst=True)
    unit_status.create(bind, checkfirst=True)
    lease_status.create(bind, checkfirst=True)

    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("address_line1", sa.Text(), nullable=False),
        sa.Column("address_line2", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=False),
        sa.Column("region", sa.Text(), nullable=False),
        sa.Column("postal_code", sa.Text(), nullable=False),
        sa.Column("country", sa.Text(), nullable=False),
        sa.Column("property_type", property_type, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_properties_owner_id", "properties", ["owner_id"])

    op.create_table(
        "units",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("bedrooms", sa.Numeric(), nullable=False),
        sa.Column("bathrooms", sa.Numeric(), nullable=False),
        sa.Column("square_feet", sa.Integer(), nullable=True),
        sa.Column("market_rent", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", unit_status, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("property_id", "label", name="uq_units_property_label"),
    )
    op.create_index("ix_units_property_id", "units", ["property_id"])

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=False),
        sa.Column("emergency_contact", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "leases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("rent_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("deposit_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("billing_day", sa.Integer(), nullable=False),
        sa.Column("status", lease_status, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"]),
        sa.PrimaryKeyConstraint("id"),
        postgresql.ExcludeConstraint(
            ("unit_id", "="),
            (sa.text("daterange(start_date, end_date, '[)')"), "&&"),
            name="exclude_overlapping_active_leases",
            where=sa.text("status = 'active'"),
            using="gist",
        ),
    )
    op.create_index("ix_leases_unit_id", "leases", ["unit_id"])
    op.create_index("ix_leases_tenant_id", "leases", ["tenant_id"])
    op.create_index("ix_leases_status", "leases", ["status"])


def downgrade() -> None:
    """Drop the domain tables and their enum types."""
    op.drop_index("ix_leases_status", table_name="leases")
    op.drop_index("ix_leases_tenant_id", table_name="leases")
    op.drop_index("ix_leases_unit_id", table_name="leases")
    op.drop_table("leases")
    op.drop_table("tenants")
    op.drop_index("ix_units_property_id", table_name="units")
    op.drop_table("units")
    op.drop_index("ix_properties_owner_id", table_name="properties")
    op.drop_table("properties")
    lease_status.drop(op.get_bind(), checkfirst=True)
    unit_status.drop(op.get_bind(), checkfirst=True)
    property_type.drop(op.get_bind(), checkfirst=True)

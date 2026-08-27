"""Lease table: term, rent amount, deposit, unit + tenant links."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, func, text
from sqlalchemy.dialects.postgresql import UUID, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.unit import Unit


class LeaseStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class Lease(Base):
    __tablename__ = "leases"
    __table_args__ = (
        Index("ix_leases_unit_id", "unit_id"),
        Index("ix_leases_tenant_id", "tenant_id"),
        Index("ix_leases_status", "status"),
        ExcludeConstraint(  # type: ignore[no-untyped-call]
            ("unit_id", "="),
            (func.daterange("start_date", "end_date", "[)"), "&&"),
            name="exclude_overlapping_active_leases",
            where=text("status = 'active'"),
            using="gist",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    rent_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    billing_day: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[LeaseStatus] = mapped_column(
        Enum(
            LeaseStatus,
            name="lease_status",
            values_callable=lambda statuses: [s.value for s in statuses],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    unit: Mapped[Unit] = relationship(back_populates="leases")
    tenant: Mapped[Tenant] = relationship(back_populates="leases")


__all__ = ["Lease", "LeaseStatus"]

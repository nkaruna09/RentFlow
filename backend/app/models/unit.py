"""Unit table (belongs to a property)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.lease import Lease
    from app.models.property import Property


class UnitStatus(str, enum.Enum):
    VACANT = "vacant"
    OCCUPIED = "occupied"
    UNAVAILABLE = "unavailable"


class Unit(Base):
    __tablename__ = "units"
    __table_args__ = (
        Index("ix_units_property_id", "property_id"),
        UniqueConstraint("property_id", "label", name="uq_units_property_label"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    bedrooms: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    bathrooms: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    square_feet: Mapped[int | None] = mapped_column(Integer, nullable=True)
    market_rent: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[UnitStatus] = mapped_column(
        Enum(
            UnitStatus,
            name="unit_status",
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

    property: Mapped[Property] = relationship(back_populates="units")
    leases: Mapped[list[Lease]] = relationship(back_populates="unit")


__all__ = ["Unit", "UnitStatus"]

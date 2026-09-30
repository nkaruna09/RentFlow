"""Maintenance request and comment tables."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.unit import Unit
    from app.models.user import User


class MaintenancePriority(str, enum.Enum):
    """Urgency assigned to a maintenance request."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EMERGENCY = "emergency"


class MaintenanceStatus(str, enum.Enum):
    """Lifecycle states for a maintenance request."""

    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class MaintenanceRequest(Base):
    """A repair or maintenance issue reported for a unit."""

    __tablename__ = "maintenance_requests"
    __table_args__ = (Index("ix_maintenance_requests_unit_id_status", "unit_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"), nullable=False
    )
    reported_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[MaintenancePriority] = mapped_column(
        Enum(
            MaintenancePriority,
            name="maintenance_priority",
            values_callable=lambda priorities: [priority.value for priority in priorities],
        ),
        nullable=False,
    )
    status: Mapped[MaintenanceStatus] = mapped_column(
        Enum(
            MaintenanceStatus,
            name="maintenance_status",
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        default=MaintenanceStatus.OPEN,
        server_default=MaintenanceStatus.OPEN.value,
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    unit: Mapped[Unit] = relationship(back_populates="maintenance_requests")
    reporter: Mapped[User] = relationship(
        back_populates="reported_maintenance_requests", foreign_keys=[reported_by]
    )
    assignee: Mapped[User | None] = relationship(
        back_populates="assigned_maintenance_requests", foreign_keys=[assigned_to]
    )
    comments: Mapped[list[MaintenanceComment]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )


class MaintenanceComment(Base):
    """A timestamped comment attached to a maintenance request."""

    __tablename__ = "maintenance_comments"
    __table_args__ = (Index("ix_maintenance_comments_request_id", "request_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maintenance_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    request: Mapped[MaintenanceRequest] = relationship(back_populates="comments")
    author: Mapped[User] = relationship(back_populates="maintenance_comments")


__all__ = [
    "MaintenanceComment",
    "MaintenancePriority",
    "MaintenanceRequest",
    "MaintenanceStatus",
]

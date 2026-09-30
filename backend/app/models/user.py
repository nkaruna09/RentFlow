"""User table: landlords, property managers, tenants."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Text, func
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.maintenance import MaintenanceComment, MaintenanceRequest


class UserRole(str, enum.Enum):
    """Roles a RentFlow user may hold."""

    LANDLORD = "landlord"
    MANAGER = "manager"
    TENANT = "tenant"


class User(Base):
    """A user who can authenticate with RentFlow."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(CITEXT(), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole, name="user_role", values_callable=lambda roles: [role.value for role in roles]
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    reported_maintenance_requests: Mapped[list[MaintenanceRequest]] = relationship(
        back_populates="reporter",
        foreign_keys="MaintenanceRequest.reported_by",
    )
    assigned_maintenance_requests: Mapped[list[MaintenanceRequest]] = relationship(
        back_populates="assignee",
        foreign_keys="MaintenanceRequest.assigned_to",
    )
    maintenance_comments: Mapped[list[MaintenanceComment]] = relationship(back_populates="author")


__all__ = ["User", "UserRole"]

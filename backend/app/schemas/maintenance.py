"""Pydantic schemas for maintenance requests and comments."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.maintenance import MaintenancePriority, MaintenanceStatus


class MaintenanceRequestCreate(BaseModel):
    """Fields accepted when a user reports a maintenance issue."""

    unit_id: uuid.UUID
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    priority: MaintenancePriority


class MaintenanceRequestUpdate(BaseModel):
    """Workflow fields that may be changed after submission."""

    priority: MaintenancePriority | None = None
    status: MaintenanceStatus | None = None
    assigned_to: uuid.UUID | None = None


class MaintenanceRequestRead(BaseModel):
    """Maintenance request fields returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    unit_id: uuid.UUID
    reported_by: uuid.UUID
    title: str
    description: str
    priority: MaintenancePriority
    status: MaintenanceStatus
    assigned_to: uuid.UUID | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MaintenanceRequestList(BaseModel):
    items: list[MaintenanceRequestRead]
    total: int
    page: int
    page_size: int


class MaintenanceCommentCreate(BaseModel):
    """Body accepted when adding a comment to a request."""

    body: str = Field(min_length=1)


class MaintenanceCommentRead(BaseModel):
    """A persisted maintenance comment returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    request_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    created_at: datetime
    updated_at: datetime


class MaintenanceCommentList(BaseModel):
    items: list[MaintenanceCommentRead]
    total: int
    page: int
    page_size: int


__all__ = [
    "MaintenanceCommentCreate",
    "MaintenanceCommentList",
    "MaintenanceCommentRead",
    "MaintenancePriority",
    "MaintenanceRequestCreate",
    "MaintenanceRequestList",
    "MaintenanceRequestRead",
    "MaintenanceRequestUpdate",
    "MaintenanceStatus",
]

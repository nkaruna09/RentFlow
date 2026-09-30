"""Maintenance request and comment endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.maintenance import MaintenancePriority, MaintenanceStatus
from app.models.user import User, UserRole
from app.schemas.maintenance import (
    MaintenanceCommentCreate,
    MaintenanceCommentRead,
    MaintenanceRequestCreate,
    MaintenanceRequestList,
    MaintenanceRequestRead,
    MaintenanceRequestUpdate,
)
from app.services import maintenance_service

router = APIRouter(prefix="/maintenance", tags=["maintenance"])
maintenance_users = require_role(UserRole.LANDLORD, UserRole.MANAGER, UserRole.TENANT)
maintenance_managers = require_role(UserRole.LANDLORD, UserRole.MANAGER)
CurrentMaintenanceUser = Annotated[User, Depends(maintenance_users)]
CurrentMaintenanceManager = Annotated[User, Depends(maintenance_managers)]


@router.get("", response_model=MaintenanceRequestList)
async def list_requests(
    current_user: CurrentMaintenanceUser,
    db: AsyncSession = Depends(get_db),
    unit_id: uuid.UUID | None = None,
    status_filter: Annotated[MaintenanceStatus | None, Query(alias="status")] = None,
    priority: MaintenancePriority | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> MaintenanceRequestList:
    requests, total = await maintenance_service.list_requests(
        db,
        current_user,
        unit_id=unit_id,
        status=status_filter,
        priority=priority,
        page=page,
        page_size=page_size,
    )
    return MaintenanceRequestList(
        items=[MaintenanceRequestRead.model_validate(request) for request in requests],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=MaintenanceRequestRead, status_code=status.HTTP_201_CREATED)
async def create_request(
    request_in: MaintenanceRequestCreate,
    current_user: CurrentMaintenanceUser,
    db: AsyncSession = Depends(get_db),
) -> MaintenanceRequestRead:
    request = await maintenance_service.create_request(db, current_user, request_in.model_dump())
    return MaintenanceRequestRead.model_validate(request)


@router.get("/{request_id}", response_model=MaintenanceRequestRead)
async def get_request(
    request_id: uuid.UUID,
    current_user: CurrentMaintenanceUser,
    db: AsyncSession = Depends(get_db),
) -> MaintenanceRequestRead:
    request = await maintenance_service.get_request(db, request_id, current_user)
    return MaintenanceRequestRead.model_validate(request)


@router.patch("/{request_id}", response_model=MaintenanceRequestRead)
async def update_request(
    request_id: uuid.UUID,
    request_in: MaintenanceRequestUpdate,
    current_user: CurrentMaintenanceManager,
    db: AsyncSession = Depends(get_db),
) -> MaintenanceRequestRead:
    request = await maintenance_service.update_visible_request(
        db,
        request_id,
        current_user,
        request_in.model_dump(exclude_unset=True),
    )
    return MaintenanceRequestRead.model_validate(request)


@router.post(
    "/{request_id}/comments",
    response_model=MaintenanceCommentRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    request_id: uuid.UUID,
    comment_in: MaintenanceCommentCreate,
    current_user: CurrentMaintenanceUser,
    db: AsyncSession = Depends(get_db),
) -> MaintenanceCommentRead:
    comment = await maintenance_service.add_comment(
        db,
        request_id,
        current_user,
        body=comment_in.body,
    )
    return MaintenanceCommentRead.model_validate(comment)

"""Lease CRUD and lifecycle endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.lease import LeaseStatus
from app.models.user import User, UserRole
from app.schemas.lease import (
    LeaseCreate,
    LeaseList,
    LeaseRead,
    LeaseRenewRequest,
    LeaseTerminateRequest,
    LeaseUpdate,
)
from app.services import lease_service

router = APIRouter(prefix="/leases", tags=["leases"])
lease_users = require_role(UserRole.LANDLORD, UserRole.MANAGER, UserRole.TENANT)
lease_managers = require_role(UserRole.LANDLORD, UserRole.MANAGER)
CurrentLeaseUser = Annotated[User, Depends(lease_users)]
CurrentLeaseManager = Annotated[User, Depends(lease_managers)]


@router.get("", response_model=LeaseList)
async def list_leases(
    current_user: CurrentLeaseUser,
    db: AsyncSession = Depends(get_db),
    unit_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    status_filter: Annotated[LeaseStatus | None, Query(alias="status")] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> LeaseList:
    leases, total = await lease_service.list_leases(
        db,
        current_user,
        unit_id=unit_id,
        tenant_id=tenant_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return LeaseList(
        items=[LeaseRead.model_validate(lease) for lease in leases],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=LeaseRead, status_code=status.HTTP_201_CREATED)
async def create_lease(
    lease_in: LeaseCreate,
    current_user: CurrentLeaseManager,
    db: AsyncSession = Depends(get_db),
) -> LeaseRead:
    lease = await lease_service.create_lease(db, current_user, lease_in.model_dump())
    return LeaseRead.model_validate(lease)


@router.get("/{lease_id}", response_model=LeaseRead)
async def get_lease(
    lease_id: uuid.UUID,
    current_user: CurrentLeaseUser,
    db: AsyncSession = Depends(get_db),
) -> LeaseRead:
    lease = await lease_service.get_lease(db, lease_id, current_user)
    return LeaseRead.model_validate(lease)


@router.patch("/{lease_id}", response_model=LeaseRead)
async def update_lease(
    lease_id: uuid.UUID,
    lease_in: LeaseUpdate,
    current_user: CurrentLeaseManager,
    db: AsyncSession = Depends(get_db),
) -> LeaseRead:
    lease = await lease_service.update_lease(
        db, lease_id, current_user, lease_in.model_dump(exclude_unset=True)
    )
    return LeaseRead.model_validate(lease)


@router.post("/{lease_id}/activate", response_model=LeaseRead)
async def activate_lease(
    lease_id: uuid.UUID,
    current_user: CurrentLeaseManager,
    db: AsyncSession = Depends(get_db),
) -> LeaseRead:
    lease = await lease_service.activate_lease(db, lease_id, current_user)
    return LeaseRead.model_validate(lease)


@router.post("/{lease_id}/renew", response_model=LeaseRead)
async def renew_lease(
    lease_id: uuid.UUID,
    current_user: CurrentLeaseManager,
    renewal: LeaseRenewRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> LeaseRead:
    # `renew` accepts an optional body; defaults create the next equal-length term.
    lease = await lease_service.renew_lease(
        db,
        lease_id,
        current_user,
        (renewal or LeaseRenewRequest()).model_dump(exclude_unset=True),
    )
    return LeaseRead.model_validate(lease)


@router.post("/{lease_id}/terminate", response_model=LeaseRead)
async def terminate_lease(
    lease_id: uuid.UUID,
    termination: LeaseTerminateRequest,
    current_user: CurrentLeaseManager,
    db: AsyncSession = Depends(get_db),
) -> LeaseRead:
    lease = await lease_service.terminate_lease(
        db,
        lease_id,
        current_user,
        reason=termination.reason,
        end_date=termination.end_date,
    )
    return LeaseRead.model_validate(lease)

"""Tenant directory and lease-history endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.lease import LeaseList, LeaseRead
from app.schemas.tenant import TenantCreate, TenantList, TenantRead, TenantUpdate
from app.services import tenant_service

router = APIRouter(prefix="/tenants", tags=["tenants"])
tenant_users = require_role(UserRole.LANDLORD, UserRole.MANAGER, UserRole.TENANT)
property_managers = require_role(UserRole.LANDLORD, UserRole.MANAGER)
CurrentTenantUser = Annotated[User, Depends(tenant_users)]
CurrentPropertyManager = Annotated[User, Depends(property_managers)]


@router.get("", response_model=TenantList)
async def list_tenants(
    current_user: CurrentTenantUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> TenantList:
    tenants, total = await tenant_service.list_tenants(
        db, current_user, page=page, page_size=page_size
    )
    return TenantList(
        items=[TenantRead.model_validate(tenant) for tenant in tenants],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_in: TenantCreate,
    _current_user: CurrentPropertyManager,
    db: AsyncSession = Depends(get_db),
) -> TenantRead:
    tenant = await tenant_service.create_tenant(db, tenant_in.model_dump())
    return TenantRead.model_validate(tenant)


@router.get("/{tenant_id}", response_model=TenantRead)
async def get_tenant(
    tenant_id: uuid.UUID,
    current_user: CurrentTenantUser,
    db: AsyncSession = Depends(get_db),
) -> TenantRead:
    tenant = await tenant_service.get_tenant(db, tenant_id, current_user)
    return TenantRead.model_validate(tenant)


@router.patch("/{tenant_id}", response_model=TenantRead)
async def update_tenant(
    tenant_id: uuid.UUID,
    tenant_in: TenantUpdate,
    current_user: CurrentTenantUser,
    db: AsyncSession = Depends(get_db),
) -> TenantRead:
    tenant = await tenant_service.update_tenant(
        db, tenant_id, current_user, tenant_in.model_dump(exclude_unset=True)
    )
    return TenantRead.model_validate(tenant)


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: uuid.UUID,
    current_user: CurrentPropertyManager,
    db: AsyncSession = Depends(get_db),
) -> Response:
    await tenant_service.delete_tenant(db, tenant_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{tenant_id}/leases", response_model=LeaseList)
async def tenant_leases(
    tenant_id: uuid.UUID,
    current_user: CurrentTenantUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> LeaseList:
    leases, total = await tenant_service.tenant_leases(
        db, tenant_id, current_user, page=page, page_size=page_size
    )
    return LeaseList(
        items=[LeaseRead.model_validate(lease) for lease in leases],
        total=total,
        page=page,
        page_size=page_size,
    )

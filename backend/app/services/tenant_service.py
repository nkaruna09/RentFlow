"""Visibility and lifecycle rules for tenant profiles."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.lease import Lease
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.repositories import tenant as tenant_repository


async def list_tenants(
    db: AsyncSession, current_user: User, *, page: int, page_size: int
) -> tuple[list[Tenant], int]:
    return await tenant_repository.list_visible(
        db, current_user.id, current_user.role, page=page, page_size=page_size
    )


async def create_tenant(db: AsyncSession, values: dict[str, object]) -> Tenant:
    return await tenant_repository.create(db, values)


async def get_tenant(db: AsyncSession, tenant_id: uuid.UUID, current_user: User) -> Tenant:
    tenant = await tenant_repository.get_visible(db, tenant_id, current_user.id, current_user.role)
    if tenant is None:
        raise NotFoundError("Tenant not found")
    return tenant


async def update_tenant(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    current_user: User,
    values: dict[str, object],
) -> Tenant:
    tenant = await get_tenant(db, tenant_id, current_user)
    return await tenant_repository.update(db, tenant, values)


async def delete_tenant(db: AsyncSession, tenant_id: uuid.UUID, current_user: User) -> None:
    tenant = await get_tenant(db, tenant_id, current_user)
    if await tenant_repository.has_leases(db, tenant.id):
        raise ConflictError("Cannot delete a tenant with lease history")
    await tenant_repository.delete(db, tenant)


async def tenant_leases(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    current_user: User,
    *,
    page: int,
    page_size: int,
) -> tuple[list[Lease], int]:
    if current_user.role not in {UserRole.LANDLORD, UserRole.MANAGER, UserRole.TENANT}:
        raise NotFoundError("Tenant not found")
    leases, total = await tenant_repository.list_leases(
        db,
        tenant_id,
        current_user.id,
        current_user.role,
        page=page,
        page_size=page_size,
    )
    if total == 0:
        # A visible tenant can legitimately have no history; distinguish it from
        # an inaccessible tenant before returning an empty list.
        await get_tenant(db, tenant_id, current_user)
    return leases, total

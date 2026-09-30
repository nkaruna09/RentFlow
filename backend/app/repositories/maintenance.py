"""Scoped persistence queries for maintenance requests and comments."""

from __future__ import annotations

import uuid
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.models.lease import Lease, LeaseStatus
from app.models.maintenance import (
    MaintenanceComment,
    MaintenancePriority,
    MaintenanceRequest,
    MaintenanceStatus,
)
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.unit import Unit
from app.models.user import User, UserRole


def _visible_requests(user_id: uuid.UUID, role: UserRole) -> Select[tuple[MaintenanceRequest]]:
    query = select(MaintenanceRequest)
    if role == UserRole.TENANT:
        return (
            query.join(Lease, MaintenanceRequest.unit_id == Lease.unit_id)
            .join(Tenant, Lease.tenant_id == Tenant.id)
            .where(Tenant.user_id == user_id, Lease.status == LeaseStatus.ACTIVE)
        )
    return (
        query.join(Unit, MaintenanceRequest.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(Property.owner_id == user_id)
    )


async def list_visible(
    db: AsyncSession,
    user_id: uuid.UUID,
    role: UserRole,
    *,
    unit_id: uuid.UUID | None,
    request_status: MaintenanceStatus | None,
    priority: MaintenancePriority | None,
    page: int,
    page_size: int,
) -> tuple[list[MaintenanceRequest], int]:
    scope = _visible_requests(user_id, role)
    if unit_id is not None:
        scope = scope.where(MaintenanceRequest.unit_id == unit_id)
    if request_status is not None:
        scope = scope.where(MaintenanceRequest.status == request_status)
    if priority is not None:
        scope = scope.where(MaintenanceRequest.priority == priority)
    total = int(await db.scalar(select(func.count()).select_from(scope.subquery())) or 0)
    result = await db.scalars(
        scope.order_by(MaintenanceRequest.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.all()), total


async def get_visible(
    db: AsyncSession,
    request_id: uuid.UUID,
    user_id: uuid.UUID,
    role: UserRole,
    *,
    for_update: bool = False,
) -> MaintenanceRequest | None:
    query = _visible_requests(user_id, role).where(MaintenanceRequest.id == request_id)
    if for_update:
        query = query.with_for_update()
    return cast(MaintenanceRequest | None, await db.scalar(query))


async def can_access_unit(
    db: AsyncSession,
    unit_id: uuid.UUID,
    user_id: uuid.UUID,
    role: UserRole,
) -> bool:
    if role == UserRole.TENANT:
        query = (
            select(Lease.id)
            .join(Tenant, Lease.tenant_id == Tenant.id)
            .where(
                Lease.unit_id == unit_id,
                Lease.status == LeaseStatus.ACTIVE,
                Tenant.user_id == user_id,
            )
        )
    else:
        query = (
            select(Unit.id)
            .join(Property, Unit.property_id == Property.id)
            .where(Unit.id == unit_id, Property.owner_id == user_id)
        )
    return await db.scalar(query) is not None


async def get_unit_owner(db: AsyncSession, unit_id: uuid.UUID) -> User | None:
    """Return the landlord/manager user that owns a unit's property."""
    return cast(
        User | None,
        await db.scalar(
            select(User)
            .join(Property, Property.owner_id == User.id)
            .join(Unit, Unit.property_id == Property.id)
            .where(Unit.id == unit_id)
        ),
    )


async def get_active_tenant_user(db: AsyncSession, unit_id: uuid.UUID) -> User | None:
    """Return the user linked to the unit's active tenant lease, if any."""
    return cast(
        User | None,
        await db.scalar(
            select(User)
            .join(Tenant, Tenant.user_id == User.id)
            .join(Lease, Lease.tenant_id == Tenant.id)
            .where(Lease.unit_id == unit_id, Lease.status == LeaseStatus.ACTIVE)
        ),
    )


async def create(db: AsyncSession, values: dict[str, object]) -> MaintenanceRequest:
    request = MaintenanceRequest(**values)
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request


async def update(db: AsyncSession, request: MaintenanceRequest) -> MaintenanceRequest:
    """Persist changes to a maintenance request."""
    await db.commit()
    await db.refresh(request)
    return request


async def create_comment(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
    author_id: uuid.UUID,
    body: str,
) -> MaintenanceComment:
    comment = MaintenanceComment(request_id=request_id, author_id=author_id, body=body)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


__all__ = [
    "can_access_unit",
    "create",
    "create_comment",
    "get_active_tenant_user",
    "get_unit_owner",
    "get_visible",
    "list_visible",
    "update",
]

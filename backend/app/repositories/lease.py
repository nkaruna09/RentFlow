"""Persistence queries for owner- and tenant-scoped leases."""

from __future__ import annotations

import uuid
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.models.lease import Lease, LeaseStatus
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.unit import Unit
from app.models.user import UserRole
from app.repositories.base import BaseRepository


class LeaseRepository(BaseRepository[Lease]):
    model = Lease


lease_repository = LeaseRepository()


def _visible_leases(user_id: uuid.UUID, role: UserRole) -> Select[tuple[Lease]]:
    query = select(Lease)
    if role == UserRole.TENANT:
        return query.join(Tenant, Lease.tenant_id == Tenant.id).where(Tenant.user_id == user_id)
    return (
        query.join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(Property.owner_id == user_id)
    )


async def list_visible(
    db: AsyncSession,
    user_id: uuid.UUID,
    role: UserRole,
    *,
    unit_id: uuid.UUID | None,
    tenant_id: uuid.UUID | None,
    lease_status: LeaseStatus | None,
    page: int,
    page_size: int,
) -> tuple[list[Lease], int]:
    scope = _visible_leases(user_id, role)
    if unit_id is not None:
        scope = scope.where(Lease.unit_id == unit_id)
    if tenant_id is not None:
        scope = scope.where(Lease.tenant_id == tenant_id)
    if lease_status is not None:
        scope = scope.where(Lease.status == lease_status)
    total = int(await db.scalar(select(func.count()).select_from(scope.subquery())) or 0)
    result = await db.scalars(
        scope.order_by(Lease.start_date.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return list(result.all()), total


async def get_visible(
    db: AsyncSession, lease_id: uuid.UUID, user_id: uuid.UUID, role: UserRole
) -> Lease | None:
    return cast(
        Lease | None,
        await db.scalar(_visible_leases(user_id, role).where(Lease.id == lease_id)),
    )


async def create(db: AsyncSession, values: dict[str, object]) -> Lease:
    return await lease_repository.create(db, values)


async def update(db: AsyncSession, lease: Lease, values: dict[str, object]) -> Lease:
    return await lease_repository.update(db, lease, values)


async def delete(db: AsyncSession, lease: Lease) -> None:
    await lease_repository.delete(db, lease)

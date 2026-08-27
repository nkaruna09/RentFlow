"""Persistence queries for tenant profiles and visible lease history."""

from __future__ import annotations

import uuid
from typing import cast

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.models.lease import Lease
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.unit import Unit
from app.models.user import UserRole


def _visible_tenants(user_id: uuid.UUID, role: UserRole) -> Select[tuple[Tenant]]:
    query = select(Tenant)
    if role == UserRole.TENANT:
        return query.where(Tenant.user_id == user_id)
    owner_lease = (
        select(Lease.id)
        .join(Unit, Lease.unit_id == Unit.id)
        .join(Property, Unit.property_id == Property.id)
        .where(Lease.tenant_id == Tenant.id, Property.owner_id == user_id)
    )
    return query.where(exists(owner_lease))


async def list_visible(
    db: AsyncSession,
    user_id: uuid.UUID,
    role: UserRole,
    *,
    page: int,
    page_size: int,
) -> tuple[list[Tenant], int]:
    scope = _visible_tenants(user_id, role)
    total = int(await db.scalar(select(func.count()).select_from(scope.subquery())) or 0)
    result = await db.scalars(
        scope.order_by(Tenant.full_name).offset((page - 1) * page_size).limit(page_size)
    )
    return list(result.all()), total


async def get_visible(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, role: UserRole
) -> Tenant | None:
    return cast(
        Tenant | None,
        await db.scalar(_visible_tenants(user_id, role).where(Tenant.id == tenant_id)),
    )


async def create(db: AsyncSession, values: dict[str, object]) -> Tenant:
    tenant = Tenant(**values)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def update(db: AsyncSession, tenant: Tenant, values: dict[str, object]) -> Tenant:
    for field, value in values.items():
        setattr(tenant, field, value)
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def delete(db: AsyncSession, tenant: Tenant) -> None:
    await db.delete(tenant)
    await db.commit()


async def has_leases(db: AsyncSession, tenant_id: uuid.UUID) -> bool:
    return bool(await db.scalar(select(exists().where(Lease.tenant_id == tenant_id))))


async def list_leases(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role: UserRole,
    *,
    page: int,
    page_size: int,
) -> tuple[list[Lease], int]:
    if role == UserRole.TENANT:
        scope = (
            select(Lease)
            .join(Tenant, Lease.tenant_id == Tenant.id)
            .where(Lease.tenant_id == tenant_id, Tenant.user_id == user_id)
        )
    else:
        scope = (
            select(Lease)
            .join(Unit, Lease.unit_id == Unit.id)
            .join(Property, Unit.property_id == Property.id)
            .where(Lease.tenant_id == tenant_id, Property.owner_id == user_id)
        )
    total = int(await db.scalar(select(func.count()).select_from(scope.subquery())) or 0)
    result = await db.scalars(
        scope.order_by(Lease.start_date.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return list(result.all()), total

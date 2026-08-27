"""Persistence queries for owner-scoped units."""

from __future__ import annotations

import uuid
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.models.property import Property
from app.models.unit import Unit, UnitStatus
from app.repositories.base import BaseRepository


class UnitRepository(BaseRepository[Unit]):
    model = Unit


unit_repository = UnitRepository()


def _owned_units(owner_id: uuid.UUID) -> Select[tuple[Unit]]:
    return (
        select(Unit)
        .join(Property, Unit.property_id == Property.id)
        .where(Property.owner_id == owner_id)
    )


async def list_for_owner(
    db: AsyncSession,
    owner_id: uuid.UUID,
    *,
    property_id: uuid.UUID | None,
    unit_status: UnitStatus | None,
    page: int,
    page_size: int,
) -> tuple[list[Unit], int]:
    scope = _owned_units(owner_id)
    if property_id is not None:
        scope = scope.where(Unit.property_id == property_id)
    if unit_status is not None:
        scope = scope.where(Unit.status == unit_status)
    total = int(await db.scalar(select(func.count()).select_from(scope.subquery())) or 0)
    result = await db.scalars(
        scope.order_by(Unit.property_id, Unit.label).offset((page - 1) * page_size).limit(page_size)
    )
    return list(result.all()), total


async def get_for_owner(db: AsyncSession, unit_id: uuid.UUID, owner_id: uuid.UUID) -> Unit | None:
    return cast(
        Unit | None,
        await db.scalar(_owned_units(owner_id).where(Unit.id == unit_id)),
    )


async def label_exists(
    db: AsyncSession,
    property_id: uuid.UUID,
    label: str,
    *,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    query = select(Unit.id).where(Unit.property_id == property_id, Unit.label == label)
    if exclude_id is not None:
        query = query.where(Unit.id != exclude_id)
    return await db.scalar(query) is not None


async def create(db: AsyncSession, values: dict[str, object]) -> Unit:
    return await unit_repository.create(db, values)


async def update(db: AsyncSession, unit: Unit, values: dict[str, object]) -> Unit:
    return await unit_repository.update(db, unit, values)


async def delete(db: AsyncSession, unit: Unit) -> None:
    await unit_repository.delete(db, unit)

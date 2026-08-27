"""Persistence queries for owner-scoped properties and units."""

from __future__ import annotations

import uuid
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.property import Property
from app.models.unit import Unit
from app.repositories.base import BaseRepository


class PropertyRepository(BaseRepository[Property]):
    model = Property


property_repository = PropertyRepository()


async def list_for_owner(
    db: AsyncSession, owner_id: uuid.UUID, *, page: int, page_size: int
) -> tuple[list[Property], int]:
    scope = select(Property).where(Property.owner_id == owner_id)
    total = int(await db.scalar(select(func.count()).select_from(scope.subquery())) or 0)
    result = await db.scalars(
        scope.order_by(Property.name).offset((page - 1) * page_size).limit(page_size)
    )
    return list(result.all()), total


async def get_for_owner(
    db: AsyncSession, property_id: uuid.UUID, owner_id: uuid.UUID
) -> Property | None:
    return cast(
        Property | None,
        await db.scalar(
            select(Property).where(Property.id == property_id, Property.owner_id == owner_id)
        ),
    )


async def create(db: AsyncSession, *, owner_id: uuid.UUID, values: dict[str, object]) -> Property:
    return await property_repository.create(db, {"owner_id": owner_id, **values})


async def update(db: AsyncSession, property_: Property, values: dict[str, object]) -> Property:
    return await property_repository.update(db, property_, values)


async def delete(db: AsyncSession, property_: Property) -> None:
    await property_repository.delete(db, property_)


async def list_units(
    db: AsyncSession, property_id: uuid.UUID, *, page: int, page_size: int
) -> tuple[list[Unit], int]:
    scope = select(Unit).where(Unit.property_id == property_id)
    total = int(await db.scalar(select(func.count()).select_from(scope.subquery())) or 0)
    result = await db.scalars(
        scope.order_by(Unit.label).offset((page - 1) * page_size).limit(page_size)
    )
    return list(result.all()), total

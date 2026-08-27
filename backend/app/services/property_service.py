"""Owner-scoped property application services."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.property import Property
from app.models.unit import Unit
from app.repositories import property as property_repository


async def list_properties(
    db: AsyncSession, owner_id: uuid.UUID, *, page: int, page_size: int
) -> tuple[list[Property], int]:
    return await property_repository.list_for_owner(db, owner_id, page=page, page_size=page_size)


async def create_property(
    db: AsyncSession, owner_id: uuid.UUID, values: dict[str, object]
) -> Property:
    return await property_repository.create(db, owner_id=owner_id, values=values)


async def get_property(db: AsyncSession, property_id: uuid.UUID, owner_id: uuid.UUID) -> Property:
    property_ = await property_repository.get_for_owner(db, property_id, owner_id)
    if property_ is None:
        raise NotFoundError("Property not found")
    return property_


async def update_property(
    db: AsyncSession,
    property_id: uuid.UUID,
    owner_id: uuid.UUID,
    values: dict[str, object],
) -> Property:
    property_ = await get_property(db, property_id, owner_id)
    return await property_repository.update(db, property_, values)


async def delete_property(db: AsyncSession, property_id: uuid.UUID, owner_id: uuid.UUID) -> None:
    property_ = await get_property(db, property_id, owner_id)
    await property_repository.delete(db, property_)


async def list_property_units(
    db: AsyncSession, property_id: uuid.UUID, owner_id: uuid.UUID, *, page: int, page_size: int
) -> tuple[list[Unit], int]:
    await get_property(db, property_id, owner_id)
    return await property_repository.list_units(db, property_id, page=page, page_size=page_size)

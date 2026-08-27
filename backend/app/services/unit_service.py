"""Owner-scoped unit application services."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.unit import Unit, UnitStatus
from app.repositories import property as property_repository
from app.repositories import unit as unit_repository


async def list_units(
    db: AsyncSession,
    owner_id: uuid.UUID,
    *,
    property_id: uuid.UUID | None,
    unit_status: UnitStatus | None,
    page: int,
    page_size: int,
) -> tuple[list[Unit], int]:
    return await unit_repository.list_for_owner(
        db,
        owner_id,
        property_id=property_id,
        unit_status=unit_status,
        page=page,
        page_size=page_size,
    )


async def create_unit(db: AsyncSession, owner_id: uuid.UUID, values: dict[str, object]) -> Unit:
    property_id = values["property_id"]
    if (
        not isinstance(property_id, uuid.UUID)
        or await property_repository.get_for_owner(db, property_id, owner_id) is None
    ):
        raise NotFoundError("Property not found")
    if await unit_repository.label_exists(db, property_id, str(values["label"])):
        raise ConflictError("A unit with this label already exists for this property")
    try:
        return await unit_repository.create(db, values)
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("A unit with this label already exists for this property") from exc


async def get_unit(db: AsyncSession, unit_id: uuid.UUID, owner_id: uuid.UUID) -> Unit:
    unit = await unit_repository.get_for_owner(db, unit_id, owner_id)
    if unit is None:
        raise NotFoundError("Unit not found")
    return unit


async def update_unit(
    db: AsyncSession,
    unit_id: uuid.UUID,
    owner_id: uuid.UUID,
    values: dict[str, object],
) -> Unit:
    unit = await get_unit(db, unit_id, owner_id)
    if "label" in values and await unit_repository.label_exists(
        db, unit.property_id, str(values["label"]), exclude_id=unit.id
    ):
        raise ConflictError("A unit with this label already exists for this property")
    try:
        return await unit_repository.update(db, unit, values)
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("A unit with this label already exists for this property") from exc


async def delete_unit(db: AsyncSession, unit_id: uuid.UUID, owner_id: uuid.UUID) -> None:
    unit = await get_unit(db, unit_id, owner_id)
    await unit_repository.delete(db, unit)

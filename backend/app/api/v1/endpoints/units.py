"""Unit CRUD endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.unit import UnitStatus
from app.models.user import User, UserRole
from app.schemas.unit import UnitCreate, UnitList, UnitRead, UnitUpdate
from app.services import unit_service

router = APIRouter(prefix="/units", tags=["units"])
unit_managers = require_role(UserRole.LANDLORD, UserRole.MANAGER)
CurrentUnitManager = Annotated[User, Depends(unit_managers)]


@router.get("", response_model=UnitList)
async def list_units(
    current_user: CurrentUnitManager,
    db: AsyncSession = Depends(get_db),
    property_id: uuid.UUID | None = None,
    status_filter: Annotated[UnitStatus | None, Query(alias="status")] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> UnitList:
    units, total = await unit_service.list_units(
        db,
        current_user.id,
        property_id=property_id,
        unit_status=status_filter,
        page=page,
        page_size=page_size,
    )
    return UnitList(
        items=[UnitRead.model_validate(unit) for unit in units],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=UnitRead, status_code=status.HTTP_201_CREATED)
async def create_unit(
    unit_in: UnitCreate,
    current_user: CurrentUnitManager,
    db: AsyncSession = Depends(get_db),
) -> UnitRead:
    unit = await unit_service.create_unit(db, current_user.id, unit_in.model_dump())
    return UnitRead.model_validate(unit)


@router.get("/{unit_id}", response_model=UnitRead)
async def get_unit(
    unit_id: uuid.UUID,
    current_user: CurrentUnitManager,
    db: AsyncSession = Depends(get_db),
) -> UnitRead:
    unit = await unit_service.get_unit(db, unit_id, current_user.id)
    return UnitRead.model_validate(unit)


@router.patch("/{unit_id}", response_model=UnitRead)
async def update_unit(
    unit_id: uuid.UUID,
    unit_in: UnitUpdate,
    current_user: CurrentUnitManager,
    db: AsyncSession = Depends(get_db),
) -> UnitRead:
    unit = await unit_service.update_unit(
        db, unit_id, current_user.id, unit_in.model_dump(exclude_unset=True)
    )
    return UnitRead.model_validate(unit)


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit(
    unit_id: uuid.UUID,
    current_user: CurrentUnitManager,
    db: AsyncSession = Depends(get_db),
) -> Response:
    await unit_service.delete_unit(db, unit_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

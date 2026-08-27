"""Property CRUD endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.property import PropertyCreate, PropertyList, PropertyRead, PropertyUpdate
from app.schemas.unit import UnitList, UnitRead
from app.services import property_service

router = APIRouter(prefix="/properties", tags=["properties"])
property_managers = require_role(UserRole.LANDLORD, UserRole.MANAGER)
CurrentPropertyManager = Annotated[User, Depends(property_managers)]


@router.get("", response_model=PropertyList)
async def list_properties(
    current_user: CurrentPropertyManager,
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> PropertyList:
    properties, total = await property_service.list_properties(
        db, current_user.id, page=page, page_size=page_size
    )
    return PropertyList(
        items=[PropertyRead.model_validate(property_) for property_ in properties],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
async def create_property(
    property_in: PropertyCreate,
    current_user: CurrentPropertyManager,
    db: AsyncSession = Depends(get_db),
) -> PropertyRead:
    property_ = await property_service.create_property(
        db, current_user.id, property_in.model_dump()
    )
    return PropertyRead.model_validate(property_)


@router.get("/{property_id}", response_model=PropertyRead)
async def get_property(
    property_id: uuid.UUID,
    current_user: CurrentPropertyManager,
    db: AsyncSession = Depends(get_db),
) -> PropertyRead:
    property_ = await property_service.get_property(db, property_id, current_user.id)
    return PropertyRead.model_validate(property_)


@router.patch("/{property_id}", response_model=PropertyRead)
async def update_property(
    property_id: uuid.UUID,
    property_in: PropertyUpdate,
    current_user: CurrentPropertyManager,
    db: AsyncSession = Depends(get_db),
) -> PropertyRead:
    property_ = await property_service.update_property(
        db, property_id, current_user.id, property_in.model_dump(exclude_unset=True)
    )
    return PropertyRead.model_validate(property_)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: uuid.UUID,
    current_user: CurrentPropertyManager,
    db: AsyncSession = Depends(get_db),
) -> Response:
    await property_service.delete_property(db, property_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{property_id}/units", response_model=UnitList)
async def list_property_units(
    property_id: uuid.UUID,
    current_user: CurrentPropertyManager,
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> UnitList:
    units, total = await property_service.list_property_units(
        db, property_id, current_user.id, page=page, page_size=page_size
    )
    return UnitList(
        items=[UnitRead.model_validate(unit) for unit in units],
        total=total,
        page=page,
        page_size=page_size,
    )

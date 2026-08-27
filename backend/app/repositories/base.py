"""Generic async CRUD repository shared by resource repositories."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Generic, TypeVar, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Small async CRUD abstraction; subclasses provide a model and scoped queries."""

    model: type[ModelT]

    async def get(self, db: AsyncSession, entity_id: Any) -> ModelT | None:
        return cast(ModelT | None, await db.get(self.model, entity_id))

    async def list(
        self,
        db: AsyncSession,
        *,
        statement: Select[tuple[ModelT]] | None = None,
        order_by: Sequence[Any] = (),
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[ModelT], int]:
        scope = statement or select(self.model)
        total = int(await db.scalar(select(func.count()).select_from(scope.subquery())) or 0)
        if order_by:
            scope = scope.order_by(*order_by)
        result = await db.scalars(scope.offset((page - 1) * page_size).limit(page_size))
        return list(result.all()), total

    async def create(self, db: AsyncSession, values: Mapping[str, object]) -> ModelT:
        entity = self.model(**dict(values))
        db.add(entity)
        await db.commit()
        await db.refresh(entity)
        return entity

    async def update(
        self, db: AsyncSession, entity: ModelT, values: Mapping[str, object]
    ) -> ModelT:
        for field, value in values.items():
            setattr(entity, field, value)
        await db.commit()
        await db.refresh(entity)
        return entity

    async def delete(self, db: AsyncSession, entity: ModelT) -> None:
        await db.delete(entity)
        await db.commit()


__all__ = ["BaseRepository"]

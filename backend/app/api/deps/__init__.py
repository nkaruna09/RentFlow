"""Shared FastAPI dependencies: db session, current user, role guards, pagination."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped async database session."""
    async with async_session_factory() as session:
        yield session


__all__ = ["get_db"]

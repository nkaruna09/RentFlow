"""Shared FastAPI dependencies: db session, current user, role guards, pagination."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.core.security import get_current_user
from app.db.session import async_session_factory
from app.models.user import User, UserRole


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped async database session."""
    async with async_session_factory() as session:
        yield session


def require_role(
    *roles: UserRole,
) -> Callable[..., Coroutine[Any, Any, User]]:
    """Build a dependency that permits only authenticated users with an allowed role."""
    if not roles:
        raise ValueError("require_role needs at least one allowed role")

    allowed_roles = frozenset(roles)

    async def role_guard(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            raise AuthorizationError("Your role does not permit this action")
        return current_user

    return role_guard


__all__ = ["get_current_user", "get_db", "require_role"]

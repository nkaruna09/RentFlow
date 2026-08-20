"""Authentication and registration business rules."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    """Create a user with a securely hashed password.

    The explicit lookup provides a useful error in the normal duplicate case;
    the integrity-error handling also covers concurrent registration attempts.
    """
    email = str(user_in.email)
    existing = await db.scalar(select(User.id).where(User.email == email))
    if existing is not None:
        raise ConflictError("A user with this email already exists")

    user = User(
        email=email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("A user with this email already exists") from exc

    await db.refresh(user)
    return user


__all__ = ["create_user"]

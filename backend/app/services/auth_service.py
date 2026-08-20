"""Authentication and registration business rules."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    is_token_revoked,
    revoke_token,
    verify_password,
)
from app.models.user import User
from app.schemas.token import TokenPair
from app.schemas.user import UserCreate

logger = logging.getLogger(__name__)


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


def _issue_token_pair(user: User) -> TokenPair:
    subject = str(user.id)
    return TokenPair(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


async def authenticate_user(db: AsyncSession, *, email: str, password: str) -> TokenPair:
    """Verify credentials and return a fresh access/refresh token pair."""
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        logger.warning("Failed login attempt", extra={"context": {"email": email}})
        raise AuthenticationError("Invalid email or password")

    return _issue_token_pair(user)


async def _resolve_refresh_token(
    db: AsyncSession, refresh_token: str
) -> tuple[User, uuid.UUID, datetime]:
    payload = decode_token(refresh_token, expected_type="refresh")
    subject = payload.get("sub")
    raw_jti = payload.get("jti")
    expires_at = payload.get("exp")
    if (
        not isinstance(subject, str)
        or not isinstance(raw_jti, str)
        or not isinstance(expires_at, int | float)
    ):
        raise AuthenticationError("Could not validate refresh token")

    try:
        user_id = uuid.UUID(subject)
        jti = uuid.UUID(raw_jti)
    except ValueError as exc:
        raise AuthenticationError("Could not validate refresh token") from exc

    if await is_token_revoked(db, jti):
        raise AuthenticationError("Refresh token has been revoked")

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Could not validate refresh token")

    return user, jti, datetime.fromtimestamp(expires_at, tz=UTC)


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenPair:
    """Rotate a valid refresh token and return a new token pair."""
    user, jti, expires_at = await _resolve_refresh_token(db, refresh_token)
    await revoke_token(
        db,
        jti=jti,
        user_id=user.id,
        expires_at=expires_at,
    )
    return _issue_token_pair(user)


async def logout_user(db: AsyncSession, refresh_token: str) -> None:
    """Revoke the presented refresh token."""
    user, jti, expires_at = await _resolve_refresh_token(db, refresh_token)
    await revoke_token(db, jti=jti, user_id=user.id, expires_at=expires_at)


__all__ = ["authenticate_user", "create_user", "logout_user", "refresh_tokens"]

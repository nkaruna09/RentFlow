"""Password hashing, JWT issue/verify, dependency-injected current user.

Access and refresh tokens are both stateless JWTs (HS256, `settings.secret_key`).
Revocation (logout, password change) is the exception path: a revoked token's
`jti` is written to the `revoked_tokens` table and checked on every verification.
Rows only need to live until the token would have expired anyway.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.db.session import get_db
from app.models.token_blocklist import RevokedToken
from app.models.user import User

settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    """Hash a plaintext password for storage."""
    return str(_pwd_context.hash(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a stored hash."""
    return bool(_pwd_context.verify(plain_password, hashed_password))


def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + expires_delta,
    }
    return str(jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm))


def create_access_token(subject: str) -> str:
    """Issue a short-lived access token for `subject` (a user id)."""
    return _create_token(subject, "access", timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(subject: str) -> str:
    """Issue a long-lived refresh token for `subject` (a user id)."""
    return _create_token(subject, "refresh", timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str, *, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Verify a token's signature and expiry, and optionally its declared type.

    Raises `AuthenticationError` for any invalid, expired, or mistyped token.
    Does not check revocation — callers that care must also call
    `is_token_revoked` (see `get_current_user`).
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
    except ExpiredSignatureError as exc:
        raise AuthenticationError("Token has expired") from exc
    except JWTError as exc:
        raise AuthenticationError("Could not validate token") from exc

    if expected_type is not None and payload.get("type") != expected_type:
        raise AuthenticationError("Incorrect token type")

    return payload


async def is_token_revoked(db: AsyncSession, jti: uuid.UUID) -> bool:
    """Check whether a token's `jti` has been blocklisted."""
    result = await db.execute(select(RevokedToken.jti).where(RevokedToken.jti == jti))
    return result.scalar_one_or_none() is not None


async def revoke_token(
    db: AsyncSession, *, jti: uuid.UUID, user_id: uuid.UUID, expires_at: datetime
) -> None:
    """Blocklist a token's `jti` until its natural expiry."""
    db.add(RevokedToken(jti=jti, user_id=user_id, expires_at=expires_at))
    await db.commit()


async def get_current_user(
    token: str | None = Depends(_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency: resolve the authenticated `User` from a bearer access token."""
    if token is None:
        raise AuthenticationError("Not authenticated")

    payload = decode_token(token, expected_type="access")

    raw_jti = payload.get("jti")
    subject = payload.get("sub")
    if raw_jti is None or subject is None:
        raise AuthenticationError("Could not validate token")

    try:
        jti = uuid.UUID(raw_jti)
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise AuthenticationError("Could not validate token") from exc

    if await is_token_revoked(db, jti):
        raise AuthenticationError("Token has been revoked")

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Could not validate token")

    return user


__all__ = [
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_current_user",
    "hash_password",
    "is_token_revoked",
    "revoke_token",
    "verify_password",
]

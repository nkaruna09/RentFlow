"""Login, refresh, registration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.token import LoginRequest, RefreshRequest, TokenPair
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import authenticate_user, create_user, refresh_tokens

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)) -> UserRead:
    """Register a new RentFlow account."""
    user = await create_user(db, user_in)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    """Exchange valid credentials for an access and refresh token pair."""
    return await authenticate_user(
        db,
        email=str(credentials.email),
        password=credentials.password,
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(request: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    """Rotate a refresh token and issue a new token pair."""
    return await refresh_tokens(db, request.refresh_token)

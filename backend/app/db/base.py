"""SQLAlchemy declarative base; imports every model so Alembic can discover them."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# Import every model module so SQLAlchemy metadata is populated for Alembic autogeneration.
from app.models import (  # noqa: F401,E402
    document,
    lease,
    maintenance,
    payment,
    property,
    tenant,
    token_blocklist,
    unit,
    user,
)

__all__ = ["Base"]

"""Persistence helpers for maintenance requests."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.maintenance import MaintenanceRequest


async def update(db: AsyncSession, request: MaintenanceRequest) -> MaintenanceRequest:
    """Persist changes to a maintenance request."""
    await db.commit()
    await db.refresh(request)
    return request


__all__ = ["update"]

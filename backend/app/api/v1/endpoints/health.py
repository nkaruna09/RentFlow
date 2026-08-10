"""Liveness / readiness probes for Azure Container Apps."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.db.session import database_is_healthy

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def health_live() -> dict[str, str]:
    return {"status": "ok", "service": "rentflow-api"}


@router.get("/ready")
async def health_ready() -> dict[str, Any]:
    try:
        await database_is_healthy()
    except Exception as exc:  # pragma: no cover - exercised by live container checks
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok", "database": "reachable"}

"""Liveness / readiness probes for Azure Container Apps."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok", "service": "rentflow-api"}


@router.get("/health/ready")
def health_ready() -> dict[str, str]:
    return {"status": "ok"}

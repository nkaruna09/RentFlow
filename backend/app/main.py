"""FastAPI application factory: middleware, CORS, routers, lifespan, health probes."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = app.state.settings
    logger = setup_logging(settings)
    logger.info("Starting RentFlow API", extra={"context": {"environment": settings.environment}})
    try:
        yield
    finally:
        logger.info("Stopping RentFlow API", extra={"context": {"environment": settings.environment}})


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title="RentFlow API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_router)

    @app.get("/")
    def root() -> dict[str, Any]:
        return {"message": "RentFlow API", "status": "ok"}

    return app


app = create_app()

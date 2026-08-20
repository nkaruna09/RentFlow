"""Domain exceptions and their HTTP handlers."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse


class RentFlowError(Exception):
    """Base exception for API-domain failures."""

    def __init__(self, detail: str, status_code: int = 500) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class NotFoundError(RentFlowError):
    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(detail=detail, status_code=404)


class ValidationError(RentFlowError):
    def __init__(self, detail: str = "Validation failed") -> None:
        super().__init__(detail=detail, status_code=400)


class AuthenticationError(RentFlowError):
    def __init__(self, detail: str = "Authentication failed") -> None:
        super().__init__(detail=detail, status_code=401)


class AuthorizationError(RentFlowError):
    def __init__(self, detail: str = "Insufficient permissions") -> None:
        super().__init__(detail=detail, status_code=403)


class ConflictError(RentFlowError):
    def __init__(self, detail: str = "Resource already exists") -> None:
        super().__init__(detail=detail, status_code=409)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach exception handlers to the FastAPI application."""

    @app.exception_handler(RentFlowError)
    async def handle_rentflow_error(request: Request, exc: RentFlowError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        field_errors = {
            ".".join(str(part) for part in error["loc"] if part != "body"): error["msg"]
            for error in exc.errors()
        }
        return JSONResponse(
            status_code=422,
            content={"detail": "Validation failed", "field_errors": field_errors},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

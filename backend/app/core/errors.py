"""Domain-level exceptions mapped to safe HTTP responses (no internal details leak to clients)."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("reelforge.errors")


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class AuthenticationError(AppError):
    status_code = 401
    code = "unauthenticated"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "forbidden"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "payload_too_large"


class ValidationFailedError(AppError):
    status_code = 422
    code = "validation_failed"


class ProviderUnavailableError(AppError):
    """An optional AI/media provider (Ollama, ComfyUI, Kokoro...) is offline or misconfigured."""

    status_code = 503
    code = "provider_unavailable"

    def __init__(self, provider: str, message: str) -> None:
        super().__init__(message, details={"provider": provider})
        self.provider = provider


class ProviderError(AppError):
    """A provider was reachable but returned an invalid or failed result."""

    status_code = 502
    code = "provider_error"

    def __init__(self, provider: str, message: str, *, retryable: bool = True) -> None:
        super().__init__(message, details={"provider": provider})
        self.provider = provider
        self.retryable = retryable


class JobCancelledError(Exception):
    """Raised inside pipeline steps when the user cancelled the job."""


def _payload(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_payload(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": [str(p) for p in e.get("loc", ())], "msg": e.get("msg", ""), "type": e.get("type", "")}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_payload("validation_failed", "Request validation failed", {"errors": errors}),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
        return JSONResponse(status_code=500, content=_payload("internal_error", "An unexpected error occurred"))

from typing import Any, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class ULPFError(Exception):
    code = "ULPF_ERROR"
    http_status = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str, *, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(ULPFError):
    code = "NOT_FOUND"
    http_status = status.HTTP_404_NOT_FOUND


class PermissionDeniedError(ULPFError):
    code = "PERMISSION_DENIED"
    http_status = status.HTTP_403_FORBIDDEN


class ValidationError(ULPFError):
    code = "VALIDATION_ERROR"
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY


class ParserError(ULPFError):
    code = "PARSER_FAILED"
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY


class QuarantineError(ULPFError):
    code = "QUARANTINE_ERROR"
    http_status = status.HTTP_400_BAD_REQUEST


class IntegrityError(ULPFError):
    code = "INTEGRITY_MISMATCH"
    http_status = status.HTTP_409_CONFLICT


def _payload(code: str, message: str, correlation_id: str | None, details: dict | None = None):
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "correlation_id": correlation_id or "",
        }
    }
    if details:
        body["error"]["details"] = details
    return body


async def ulpf_exception_handler(request: Request, exc: ULPFError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=_payload(exc.code, exc.message, getattr(request.state, "correlation_id", None), exc.details),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = "HTTP_ERROR"
    if exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"
    elif exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 429:
        code = "RATE_LIMITED"
    return JSONResponse(
        status_code=exc.status_code,
        content=_payload(code, str(exc.detail), getattr(request.state, "correlation_id", None)),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_payload(
            "VALIDATION_ERROR",
            "Request validation failed",
            getattr(request.state, "correlation_id", None),
            {"errors": exc.errors()},
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=_payload(
            "INTERNAL_ERROR",
            "An internal error occurred",
            getattr(request.state, "correlation_id", None),
        ),
    )
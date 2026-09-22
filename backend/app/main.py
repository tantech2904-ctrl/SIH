from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.core.errors import (
    ULPFError, generic_exception_handler, http_exception_handler,
    ulpf_exception_handler, validation_exception_handler,
)
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import limiter
from app.db.init_db import init_db
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cid = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        request.state.correlation_id = cid
        response = await call_next(request)
        response.headers["x-correlation-id"] = cid
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    log.info("app.startup", env=settings.APP_ENV, version=settings.APP_VERSION)

    # Optional Syslog UDP listener (asyncio task; off unless enabled).
    syslog_listener = None
    if settings.SYSLOG_UDP_ENABLED:
        # Imported lazily so a missing optional dependency cannot break boot.
        from app.syslog.udp_listener import SyslogUdpListener

        syslog_listener = SyslogUdpListener(
            host=settings.SYSLOG_UDP_HOST,
            port=settings.SYSLOG_UDP_PORT,
        )
        try:
            await syslog_listener.start()
        except OSError as e:
            log.error(
                "syslog.udp.bind_failed",
                host=settings.SYSLOG_UDP_HOST,
                port=settings.SYSLOG_UDP_PORT,
                error=str(e),
            )
            syslog_listener = None

    try:
        yield
    finally:
        if syslog_listener is not None:
            await syslog_listener.stop()
        log.info("app.shutdown")


app = FastAPI(
    title="ULPF — Universal Log Pre-Processing Framework",
    description=(
        "Vendor-agnostic security log preprocessing and canonical normalization layer.\n\n"
        "Team The Beetles · SIH 2026 · Problem Statement 26156"
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": {"code": "RATE_LIMITED", "message": "Rate limit exceeded",
                            "correlation_id": getattr(request.state, "correlation_id", None)}},
    )


app.add_exception_handler(ULPFError, ulpf_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-correlation-id"],
)

app.include_router(api_v1_router, prefix=settings.API_PREFIX)


@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api": settings.API_PREFIX,
    }
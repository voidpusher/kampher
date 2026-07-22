"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.routers import (
    chat,
    graph,
    health,
    meta,
    opportunities,
    reports,
    search,
    tech_polls,
    trends,
)
from app.core.config import get_settings
from app.core.exceptions import KampherError
from app.core.logging import bind_request_context, configure_logging, get_logger

log = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log.info("kampher api starting", env=get_settings().env.value)
    yield
    from app.db.session import get_async_engine

    await get_async_engine().dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Kampher API",
        description="Opportunity intelligence: ranked, explained startup opportunities "
        "mined from public internet conversations.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        rid = bind_request_context(request.headers.get("x-request-id"))
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > 64 * 1024:
            response = JSONResponse(
                status_code=413,
                content={"detail": "Request body is too large."},
            )
        else:
            response = await call_next(request)
        response.headers["x-request-id"] = rid
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["referrer-policy"] = "strict-origin-when-cross-origin"
        response.headers["permissions-policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path == "/chat":
            response.headers["cache-control"] = "no-store"
        return response

    @app.exception_handler(KampherError)
    async def domain_error_handler(_: Request, exc: KampherError) -> JSONResponse:
        # RFC 7807 problem details.
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.problem(),
            media_type="application/problem+json",
        )

    app.include_router(health.router)
    app.include_router(opportunities.router)
    app.include_router(search.router)
    app.include_router(chat.router)
    app.include_router(trends.router)
    app.include_router(tech_polls.router)
    app.include_router(reports.router)
    app.include_router(graph.router)
    app.include_router(meta.router)
    return app


app = create_app()

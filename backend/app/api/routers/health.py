"""Liveness + readiness probes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Response
from sqlalchemy import select, text

from app.api.deps import SessionDep
from app.collectors.registry import enabled_collectors
from app.models import SourceCursor
from app.schemas.api import HealthOut
from app.services.ingestion_monitor import ExpectedStream, evaluate_stream_health, is_healthy

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthOut)
async def live() -> HealthOut:
    return HealthOut(status="ok", checks={})


@router.get("/ready", response_model=HealthOut)
async def ready(response: Response) -> HealthOut:
    checks: dict[str, str] = {}

    async def check_postgres() -> None:
        from app.db.session import get_async_sessionmaker

        try:
            async with get_async_sessionmaker()() as session:
                await session.execute(text("SELECT 1"))
            checks["postgres"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["postgres"] = f"error: {type(exc).__name__}"

    async def check_redis() -> None:
        import redis.asyncio as aioredis

        from app.core.config import get_settings

        if not get_settings().redis_health_check:
            checks["redis"] = "skipped"
            return
        try:
            client = aioredis.from_url(  # type: ignore[no-untyped-call]
                get_settings().redis_url
            )
            await client.ping()
            await client.aclose()
            checks["redis"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["redis"] = f"error: {type(exc).__name__}"

    async def check_qdrant() -> None:
        from app.vector.store import get_vector_store

        try:
            await asyncio.to_thread(get_vector_store().client.get_collections)
            checks["qdrant"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["qdrant"] = f"error: {type(exc).__name__}"

    await asyncio.gather(check_postgres(), check_redis(), check_qdrant())
    healthy = all(v in {"ok", "skipped"} for v in checks.values())
    if not healthy:
        response.status_code = 503
    return HealthOut(status="ok" if healthy else "degraded", checks=checks)


@router.get("/data", response_model=HealthOut)
async def data_health(session: SessionDep, response: Response) -> HealthOut:
    """Report whether every configured source stream is running successfully."""
    expected = [
        ExpectedStream(
            source=collector.source,
            stream=stream,
            # Stack Overflow intentionally runs every two hours to protect its
            # anonymous quota; public feeds run every fifteen minutes.
            stale_after_minutes=180 if collector.source.value == "stackoverflow" else 60,
        )
        for collector in enabled_collectors()
        for stream in collector.streams()
    ]
    cursors = list(await session.scalars(select(SourceCursor)))
    checks = evaluate_stream_health(expected, cursors)
    healthy = is_healthy(checks)
    if not healthy:
        response.status_code = 503
    return HealthOut(status="ok" if healthy else "degraded", checks=checks)

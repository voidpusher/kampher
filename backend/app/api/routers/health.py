"""Liveness + readiness probes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Response
from sqlalchemy import text

from app.schemas.api import HealthOut

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

"""Structured logging.

JSON logs in staging/prod (machine-ingestable), pretty console in dev.
``bind_request_context`` propagates a request/task id through every log line
emitted while handling that unit of work, including inside Celery tasks.
"""

from __future__ import annotations

import logging
import sys
import uuid

import structlog

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()

    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer: structlog.typing.Processor = (
        structlog.dev.ConsoleRenderer() if settings.is_dev else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(message)s",
        stream=sys.stdout,
    )
    # Quiet noisy third-party loggers; our own logs carry the signal.
    for noisy in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def bind_request_context(request_id: str | None = None, **extra: str) -> str:
    rid = request_id or uuid.uuid4().hex[:12]
    structlog.contextvars.bind_contextvars(request_id=rid, **extra)
    return rid


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    # PrintLogger has no .name attribute, so carry the name as a bound field.
    return structlog.get_logger().bind(logger=name)  # type: ignore[no-any-return]

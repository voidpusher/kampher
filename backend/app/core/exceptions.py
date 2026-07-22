"""Typed exception hierarchy.

Every domain error maps to an RFC 7807 problem response in the API layer.
Workers catch ``RetryableError`` subclasses for automatic retry and let the
rest surface as task failures.
"""

from __future__ import annotations

from typing import Any


class KampherError(Exception):
    """Base class for all domain errors."""

    status_code: int = 500
    title: str = "Internal error"

    def __init__(self, detail: str = "", **context: Any) -> None:
        super().__init__(detail or self.title)
        self.detail = detail or self.title
        self.context = context

    def problem(self) -> dict[str, Any]:
        """RFC 7807 problem-details payload."""
        return {
            "type": f"https://kampher.dev/errors/{type(self).__name__}",
            "title": self.title,
            "status": self.status_code,
            "detail": self.detail,
            **({"context": self.context} if self.context else {}),
        }


class NotFoundError(KampherError):
    status_code = 404
    title = "Resource not found"


class ValidationFailedError(KampherError):
    status_code = 422
    title = "Validation failed"


class RetryableError(KampherError):
    """Transient failure — safe to retry with backoff."""

    status_code = 503
    title = "Temporarily unavailable"


class RateLimitedError(RetryableError):
    title = "Upstream rate limit hit"

    def __init__(self, detail: str = "", retry_after: float | None = None, **ctx: Any) -> None:
        super().__init__(detail, **ctx)
        self.retry_after = retry_after


class SourceUnavailableError(RetryableError):
    title = "Source unavailable"


class LLMError(RetryableError):
    title = "LLM call failed"


class LLMOutputInvalidError(KampherError):
    """Model returned output that failed schema validation after retries."""

    status_code = 502
    title = "LLM output invalid"


class ConfigurationError(KampherError):
    title = "Configuration error"

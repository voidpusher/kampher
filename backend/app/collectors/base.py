"""Collector plugin contract.

A collector = streams (units of sync state) + ``collect(stream, cursor)``.
Rate limiting and retry-with-backoff are provided here so every source plugin
is only responsible for its API shape and normalization.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.collectors.rate_limit import TokenBucket
from app.collectors.schema import CollectResult
from app.core.config import Settings, get_settings
from app.core.exceptions import RateLimitedError, SourceUnavailableError
from app.core.logging import get_logger
from app.models.enums import Source


class BaseCollector(ABC):
    source: ClassVar[Source]
    requests_per_second: ClassVar[float] = 1.0
    max_attempts: ClassVar[int] = 4

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.rate = TokenBucket(rate=self.requests_per_second)
        self.log = get_logger(f"collector.{self.source.value}")

    # ── plugin surface ──────────────────────────────────────────────────

    @abstractmethod
    def enabled(self) -> bool:
        """Whether this source is configured (credentials present etc.)."""

    @abstractmethod
    def streams(self) -> list[str]:
        """Independent sync units: subreddits, repos, queries, …"""

    @abstractmethod
    async def collect(self, stream: str, cursor: dict[str, Any]) -> CollectResult:
        """Fetch new documents for one stream since ``cursor``."""

    # ── shared plumbing ─────────────────────────────────────────────────

    async def _request_json(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> Any:
        """Rate-limited request with exponential backoff + jitter.

        429/5xx are transient (retried); 4xx are config/programming errors
        and surface immediately.
        """
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential_jitter(initial=2, max=60),
            retry=retry_if_exception_type((RateLimitedError, SourceUnavailableError)),
            reraise=True,
        ):
            with attempt:
                await self.rate.acquire()
                try:
                    response = await client.request(method, url, **kwargs)
                except httpx.TransportError as exc:
                    raise SourceUnavailableError(str(exc), url=url) from exc

                if response.status_code == 429:
                    retry_after = float(response.headers.get("retry-after", 0)) or None
                    raise RateLimitedError(url=url, retry_after=retry_after)
                if response.status_code >= 500:
                    raise SourceUnavailableError(f"{response.status_code} from upstream", url=url)
                response.raise_for_status()
                return response.json()

    def http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=httpx.Timeout(30.0), follow_redirects=True)

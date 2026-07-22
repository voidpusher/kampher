"""Async token-bucket rate limiter, one per collector instance."""

from __future__ import annotations

import asyncio
import time


class TokenBucket:
    """Classic token bucket: ``rate`` tokens/sec, burst up to ``capacity``.

    ``acquire()`` sleeps until a token is available, so callers just await it
    before every upstream request and never think about pacing again.
    """

    def __init__(self, rate: float, capacity: float | None = None) -> None:
        if rate <= 0:
            raise ValueError("rate must be positive")
        self._rate = rate
        self._capacity = capacity if capacity is not None else max(rate, 1.0)
        self._tokens = self._capacity
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        self._tokens = min(self._capacity, self._tokens + (now - self._last_refill) * self._rate)
        self._last_refill = now

    async def acquire(self, tokens: float = 1.0) -> None:
        async with self._lock:
            while True:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                deficit = tokens - self._tokens
                await asyncio.sleep(deficit / self._rate)

"""Small in-process rate limiter for expensive public endpoints.

Render runs a single API process, so a fixed-window limiter is enough to protect
the public search and chat surfaces without adding Redis as a production dependency.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class FixedWindowRateLimiter:
    _MAX_CLIENT_KEYS = 10_000

    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> float | None:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            if key not in self._requests and len(self._requests) >= self._MAX_CLIENT_KEYS:
                stale_keys = [
                    client_key
                    for client_key, timestamps in self._requests.items()
                    if not timestamps or timestamps[-1] <= cutoff
                ]
                for stale_key in stale_keys:
                    del self._requests[stale_key]
            bucket_key = (
                key
                if key in self._requests or len(self._requests) < self._MAX_CLIENT_KEYS
                else "overflow"
            )
            requests = self._requests[bucket_key]
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= limit:
                return max(1.0, window_seconds - (now - requests[0]))
            requests.append(now)
            return None


limiter = FixedWindowRateLimiter()


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", maxsplit=1)[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "unknown"


def enforce_chat_rate_limit(request: Request) -> None:
    _enforce(request, scope="chat", limit=10, window_seconds=60)


def enforce_search_rate_limit(request: Request) -> None:
    _enforce(request, scope="search", limit=60, window_seconds=60)


def _enforce(request: Request, *, scope: str, limit: int, window_seconds: int) -> None:
    retry_after = limiter.check(
        f"{scope}:{_client_key(request)}",
        limit=limit,
        window_seconds=window_seconds,
    )
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait before trying again.",
            headers={"Retry-After": str(int(retry_after))},
        )

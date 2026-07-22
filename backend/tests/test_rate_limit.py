from __future__ import annotations

from app.core.rate_limit import FixedWindowRateLimiter


def test_rate_limiter_blocks_after_limit() -> None:
    limiter = FixedWindowRateLimiter()

    assert limiter.check("client", limit=2, window_seconds=60) is None
    assert limiter.check("client", limit=2, window_seconds=60) is None
    assert limiter.check("client", limit=2, window_seconds=60) is not None


def test_rate_limiter_keeps_scopes_independent() -> None:
    limiter = FixedWindowRateLimiter()

    assert limiter.check("chat:client", limit=1, window_seconds=60) is None
    assert limiter.check("search:client", limit=1, window_seconds=60) is None

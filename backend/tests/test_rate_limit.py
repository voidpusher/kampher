from __future__ import annotations

from starlette.requests import Request

from app.core.rate_limit import FixedWindowRateLimiter, _client_key


def test_rate_limiter_blocks_after_limit() -> None:
    limiter = FixedWindowRateLimiter()

    assert limiter.check("client", limit=2, window_seconds=60) is None
    assert limiter.check("client", limit=2, window_seconds=60) is None
    assert limiter.check("client", limit=2, window_seconds=60) is not None


def test_rate_limiter_keeps_scopes_independent() -> None:
    limiter = FixedWindowRateLimiter()

    assert limiter.check("chat:client", limit=1, window_seconds=60) is None
    assert limiter.check("search:client", limit=1, window_seconds=60) is None


def test_client_key_ignores_spoofed_leftmost_forwarded_address() -> None:
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/chat",
            "headers": [(b"x-forwarded-for", b"198.51.100.10, 203.0.113.25")],
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
        }
    )

    assert _client_key(request) == "203.0.113.25"


def test_client_key_rejects_invalid_forwarded_address() -> None:
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/chat",
            "headers": [(b"x-forwarded-for", b"not-an-ip")],
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
        }
    )

    assert _client_key(request) == "127.0.0.1"

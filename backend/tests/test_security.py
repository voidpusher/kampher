from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.api.main as api_main
from app.core.config import Environment, Settings


def test_api_sets_defensive_browser_headers() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["content-security-policy"] == (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    )
    assert response.headers["cross-origin-opener-policy"] == "same-origin"


def test_production_disables_interactive_api_documentation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        env=Environment.PROD,
        cors_origins=["https://kampher.vercel.app"],
    )
    monkeypatch.setattr(api_main, "get_settings", lambda: settings)

    production_app = api_main.create_app()

    assert production_app.docs_url is None
    assert production_app.redoc_url is None
    assert production_app.openapi_url is None


def test_production_rejects_wildcard_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(env=Environment.PROD, cors_origins=["*"])
    monkeypatch.setattr(api_main, "get_settings", lambda: settings)

    with pytest.raises(RuntimeError, match="wildcard CORS"):
        api_main.create_app()

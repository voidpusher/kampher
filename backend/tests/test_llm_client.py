from __future__ import annotations

import asyncio
from types import SimpleNamespace

from pydantic import BaseModel

from app.ai.llm.anthropic_client import AnthropicClient
from app.ai.llm.base import ModelTier
from app.ai.llm.client import get_llm_client
from app.ai.llm.gemini_client import GeminiClient
from app.core.config import Settings, get_settings


def test_factory_selects_anthropic(monkeypatch) -> None:
    monkeypatch.setenv("KAMPHER_LLM_PROVIDER", "anthropic")
    get_settings.cache_clear()
    get_llm_client.cache_clear()

    assert isinstance(get_llm_client(), AnthropicClient)


def test_factory_selects_gemini(monkeypatch) -> None:
    monkeypatch.setenv("KAMPHER_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    get_settings.cache_clear()
    get_llm_client.cache_clear()

    assert isinstance(get_llm_client(), GeminiClient)


def test_gemini_model_tiers(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    settings = Settings(llm_model="deep-model", llm_model_fast="fast-model")
    client = GeminiClient(settings)

    assert client._model_for(ModelTier.DEEP) == "deep-model"
    assert client._model_for(ModelTier.FAST) == "fast-model"


def test_gemini_closes_loop_scoped_client(monkeypatch) -> None:
    class HealthResult(BaseModel):
        ok: bool

    class FakeAioClient:
        def __init__(self) -> None:
            self.models = self
            self.closed = False

        async def generate_content(self, **_kwargs):  # type: ignore[no-untyped-def]
            return SimpleNamespace(text='{"ok": true}', usage_metadata=None)

        async def aclose(self) -> None:
            self.closed = True

    fake_aio = FakeAioClient()
    monkeypatch.setattr(
        "app.ai.llm.gemini_client.genai.Client",
        lambda **_kwargs: SimpleNamespace(aio=fake_aio),
    )
    client = GeminiClient(Settings(gemini_api_key="test-key"))

    response = asyncio.run(
        client._call_with_retry(
            model="fast-model",
            system="Return JSON",
            prompt="health",
            schema=HealthResult,
            tier=ModelTier.FAST,
            max_tokens=32,
        )
    )

    assert response.text == '{"ok": true}'
    assert fake_aio.closed is True

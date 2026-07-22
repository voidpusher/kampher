"""Configured LLM provider factory."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from app.ai.llm.anthropic_client import AnthropicClient
from app.ai.llm.gemini_client import GeminiClient
from app.core.config import get_settings
from app.core.exceptions import ConfigurationError

if TYPE_CHECKING:
    from app.ai.llm.base import BaseLLMClient


@lru_cache
def get_llm_client() -> BaseLLMClient:
    provider = get_settings().llm_provider.strip().lower()
    if provider == "anthropic":
        return AnthropicClient()
    if provider == "gemini":
        return GeminiClient()
    raise ConfigurationError(
        f"Unsupported LLM provider: {provider}",
        supported_providers=["anthropic", "gemini"],
    )

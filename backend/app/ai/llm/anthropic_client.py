"""Anthropic implementation of the LLM interface.

Structured output is enforced with a forced tool call whose input schema is
the caller's Pydantic JSON schema — the model physically cannot return prose.
Validation failures are fed back to the model once before giving up, and all
transient API errors retry with exponential backoff.
"""

from __future__ import annotations

import time
from typing import TypeVar, cast

import anthropic
from pydantic import BaseModel, ValidationError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.ai.llm.base import BaseLLMClient, LLMResult, LLMUsage, ModelTier
from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError, LLMError, LLMOutputInvalidError
from app.core.logging import get_logger

T = TypeVar("T", bound=BaseModel)

_EMIT_TOOL = "emit_result"


class AnthropicClient(BaseLLMClient):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if self.settings.anthropic_api_key is None:
            raise ConfigurationError("ANTHROPIC_API_KEY is not set")
        self._client = anthropic.AsyncAnthropic(
            api_key=self.settings.anthropic_api_key.get_secret_value()
        )
        self.log = get_logger("llm.anthropic")

    def _model_for(self, tier: ModelTier) -> str:
        return self.settings.llm_model if tier is ModelTier.DEEP else self.settings.llm_model_fast

    async def extract(
        self,
        *,
        system: str,
        user: str,
        schema: type[T],
        tier: ModelTier = ModelTier.FAST,
        max_tokens: int = 2048,
    ) -> LLMResult[T]:
        model = self._model_for(tier)
        tool = cast(
            "anthropic.types.ToolParam",
            {
                "name": _EMIT_TOOL,
                "description": "Emit the extraction result. Always call this exactly once.",
                "input_schema": schema.model_json_schema(),
            },
        )
        messages: list[anthropic.types.MessageParam] = [{"role": "user", "content": user}]

        last_validation_error: ValidationError | None = None
        for validation_round in range(2):  # one repair round on schema violation
            response = await self._call_with_retry(
                model=model,
                system=system,
                messages=messages,
                tool=tool,
                max_tokens=max_tokens,
            )
            started = time.monotonic()
            tool_use = next(
                (b for b in response.content if b.type == "tool_use" and b.name == _EMIT_TOOL),
                None,
            )
            if tool_use is None:
                raise LLMOutputInvalidError("model did not call the emit tool", model=model)

            try:
                data = schema.model_validate(tool_use.input)
            except ValidationError as exc:
                last_validation_error = exc
                self.log.warning(
                    "llm output failed validation, requesting repair",
                    model=model,
                    round=validation_round,
                    errors=exc.error_count(),
                )
                messages = [
                    *messages,
                    {"role": "assistant", "content": response.content},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "is_error": True,
                                "content": f"Schema validation failed:\n{exc}\n"
                                f"Call {_EMIT_TOOL} again with corrected input.",
                            }
                        ],
                    },
                ]
                continue

            usage = LLMUsage(
                model=model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                latency_ms=int((time.monotonic() - started) * 1000),
            )
            return LLMResult(data=data, usage=usage)

        raise LLMOutputInvalidError(
            f"output failed schema validation after repair: {last_validation_error}",
            model=model,
            schema=schema.__name__,
        )

    async def _call_with_retry(
        self,
        *,
        model: str,
        system: str,
        messages: list[anthropic.types.MessageParam],
        tool: anthropic.types.ToolParam,
        max_tokens: int,
    ) -> anthropic.types.Message:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(4),
            wait=wait_exponential_jitter(initial=2, max=45),
            retry=retry_if_exception_type(LLMError),
            reraise=True,
        ):
            with attempt:
                try:
                    return await self._client.messages.create(
                        model=model,
                        system=system,
                        messages=messages,
                        tools=[tool],
                        tool_choice={"type": "tool", "name": _EMIT_TOOL},
                        max_tokens=max_tokens,
                    )
                except (
                    anthropic.RateLimitError,
                    anthropic.APIConnectionError,
                    anthropic.InternalServerError,
                ) as exc:
                    raise LLMError(str(exc), model=model) from exc
        raise AssertionError("unreachable")  # AsyncRetrying always returns or raises

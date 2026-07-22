"""Google Gemini implementation of Kampher's structured LLM interface."""

from __future__ import annotations

import time
from typing import TypeVar

from google import genai
from google.genai import errors, types
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
_FALLBACK_MODEL = "gemini-3.1-flash-lite"


class GeminiClient(BaseLLMClient):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if self.settings.gemini_api_key is None:
            raise ConfigurationError("GEMINI_API_KEY is not set")
        self._client = genai.Client(api_key=self.settings.gemini_api_key.get_secret_value())
        self.log = get_logger("llm.gemini")

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
        prompt = user
        last_validation_error: ValidationError | None = None

        for validation_round in range(2):
            started = time.monotonic()
            response = await self._call_with_retry(
                model=model,
                system=system,
                prompt=prompt,
                schema=schema,
                tier=tier,
                max_tokens=max_tokens,
            )
            try:
                data = schema.model_validate_json(response.text or "")
            except ValidationError as exc:
                last_validation_error = exc
                self.log.warning(
                    "llm output failed validation, requesting repair",
                    model=model,
                    round=validation_round,
                    errors=exc.error_count(),
                )
                prompt = (
                    f"{user}\n\nYour previous response failed schema validation:\n{exc}\n"
                    "Return a corrected result that matches the requested schema."
                )
                continue

            metadata = response.usage_metadata
            usage = LLMUsage(
                model=model,
                input_tokens=(metadata.prompt_token_count or 0) if metadata else 0,
                output_tokens=(metadata.candidates_token_count or 0) if metadata else 0,
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
        prompt: str,
        schema: type[BaseModel],
        tier: ModelTier,
        max_tokens: int,
    ) -> types.GenerateContentResponse:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(4),
            wait=wait_exponential_jitter(initial=2, max=45),
            retry=retry_if_exception_type(LLMError),
            reraise=True,
        ):
            with attempt:

                async def generate(selected_model: str) -> types.GenerateContentResponse:
                    return await self._client.aio.models.generate_content(
                        model=selected_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system,
                            max_output_tokens=max_tokens,
                            thinking_config=types.ThinkingConfig(
                                thinking_level=("medium" if tier is ModelTier.DEEP else "minimal")
                            ),
                            response_mime_type="application/json",
                            response_json_schema=schema.model_json_schema(),
                        ),
                    )

                try:
                    return await generate(model)
                except errors.APIError as exc:
                    if exc.code in {429, 503} and model != _FALLBACK_MODEL:
                        self.log.warning(
                            "primary gemini model busy; trying latency fallback",
                            model=model,
                            fallback_model=_FALLBACK_MODEL,
                            status_code=exc.code,
                        )
                        try:
                            return await generate(_FALLBACK_MODEL)
                        except errors.APIError as fallback_exc:
                            exc = fallback_exc
                    if exc.code == 429 or exc.code >= 500:
                        raise LLMError(str(exc), model=model, status_code=exc.code) from exc
                    raise LLMOutputInvalidError(
                        str(exc), model=model, status_code=exc.code
                    ) from exc
        raise AssertionError("unreachable")

"""Provider-agnostic LLM interface.

Two tiers instead of one model everywhere:
- ``fast``  — high-volume per-document classification/extraction,
- ``deep``  — cluster-level reasoning (opportunity generation, scoring, reports).

Every call is a *structured extraction*: the caller supplies a Pydantic
schema and gets a validated instance back. Free-text parsing is banned by
construction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ModelTier(StrEnum):
    FAST = "fast"
    DEEP = "deep"


@dataclass(slots=True)
class LLMUsage:
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


@dataclass(slots=True)
class LLMResult[TData: BaseModel]:
    data: TData
    usage: LLMUsage


class BaseLLMClient(ABC):
    @abstractmethod
    async def extract(
        self,
        *,
        system: str,
        user: str,
        schema: type[T],
        tier: ModelTier = ModelTier.FAST,
        max_tokens: int = 2048,
    ) -> LLMResult[T]:
        """Run one structured extraction; returns a validated ``schema`` instance."""

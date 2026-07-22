"""Collector registry.

Adding a source = write the collector module and decorate it with
``@register``. Schedulers, ingestion, and the pipeline discover it here.
"""

from __future__ import annotations

from app.collectors.base import BaseCollector
from app.models.enums import Source

_REGISTRY: dict[Source, type[BaseCollector]] = {}


def register(cls: type[BaseCollector]) -> type[BaseCollector]:
    if cls.source in _REGISTRY:
        raise ValueError(f"duplicate collector for source {cls.source}")
    _REGISTRY[cls.source] = cls
    return cls


def all_collectors() -> dict[Source, type[BaseCollector]]:
    # Import triggers registration; kept inside the function to avoid cycles.
    import app.collectors.sources  # noqa: F401

    return dict(_REGISTRY)


def enabled_collectors() -> list[BaseCollector]:
    instances = [cls() for cls in all_collectors().values()]
    return [c for c in instances if c.enabled()]


def get_collector(source: Source) -> BaseCollector:
    collector = all_collectors().get(source)
    if collector is None:
        raise KeyError(f"no collector registered for {source}")
    return collector()

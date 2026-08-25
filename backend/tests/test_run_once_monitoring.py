from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from app.models.enums import Source
from app.services.ingestion import IngestionService
from app.workers import run_once


def test_collection_command_fails_after_isolating_stream_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collector = SimpleNamespace(
        source=Source.HACKERNEWS,
        streams=lambda: ["problems"],
    )
    monkeypatch.setattr("app.collectors.registry.enabled_collectors", lambda: [collector])

    def fail_collection(self: IngestionService, source: Source, stream: str) -> list[Any]:
        raise RuntimeError("upstream unavailable")

    monkeypatch.setattr(IngestionService, "collect_stream", fail_collection)

    @contextmanager
    def fake_session() -> Any:
        yield object()

    monkeypatch.setattr(run_once, "worker_session", fake_session)

    with pytest.raises(SystemExit) as exc_info:
        run_once.main("collect")

    assert exc_info.value.code == 1

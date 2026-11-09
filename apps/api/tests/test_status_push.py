"""Status page push: the HTTP client it opens itself is closed again (no database)."""

from __future__ import annotations

from typing import Any, cast

import httpx
import pytest

from handball_api.core.config import Settings
from handball_api.services import monitoring
from handball_api.services.context import Ctx


async def test_push_status_closes_its_own_client(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def no_checks(*a: Any, **k: Any) -> list[Any]:
        return []

    opened: list[httpx.AsyncClient] = []
    real = httpx.AsyncClient

    def client(**kwargs: Any) -> httpx.AsyncClient:
        c = real(**kwargs, transport=httpx.MockTransport(lambda r: httpx.Response(503)))
        opened.append(c)
        return c

    monkeypatch.setattr(monitoring, "run_checks", no_checks)
    monkeypatch.setattr(httpx, "AsyncClient", client)
    settings.status_page_push_url = "https://status.example.test/api/components"
    none = cast(Any, None)
    ctx = Ctx(db=none, settings=settings, email=none, storage=none)
    assert await monitoring.push_status(ctx) == []  # a failed push is logged, not raised
    assert len(opened) == 1 and opened[0].is_closed
    # a client passed in stays open for its owner
    own = real(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    await monitoring.push_status(ctx, own)
    assert not own.is_closed
    await own.aclose()

"""Runs against docker compose services: `make test-integration`."""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

from handball_api.core.config import Settings
from handball_api.main import create_app

pytestmark = pytest.mark.integration


async def test_readyz_against_real_services() -> None:
    settings = Settings(
        env="test",
        database_url=os.environ.get(
            "HB_DATABASE_URL", "postgresql+asyncpg://handball:handball@localhost:5432/handball"
        ),
    )
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as c,
    ):
        r = await c.get("/readyz")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ok"

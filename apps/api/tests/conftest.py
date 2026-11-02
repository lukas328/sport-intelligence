from __future__ import annotations

from collections.abc import AsyncIterator, Callable

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from handball_api.core.config import Settings
from handball_api.main import create_app
from handball_api.routers.health import get_checks
from handball_api.services.health import Check


@pytest.fixture
def settings() -> Settings:
    return Settings(
        env="test", log_json=False, database_url="postgresql+asyncpg://x:y@127.0.0.1:1/z"
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def override_checks(app: FastAPI) -> Callable[[dict[str, Check]], None]:
    def _set(checks: dict[str, Check]) -> None:
        app.dependency_overrides[get_checks] = lambda: checks

    return _set


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

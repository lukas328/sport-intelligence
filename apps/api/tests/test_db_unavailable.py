"""The database out of reach (no free connection, the server refusing one) is no fault of the
request: 503 problem+json with Retry-After, logged with its traceback, never a bare 500.

Production (Container Apps on a small Postgres) answered 500 on a few reads of the roster and the
match graphics, each followed by a 200 on the same URL a second later: the pattern of a
connection the server refuses while the pools of all API processes together exceed its limit."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from structlog.testing import capture_logs

from handball_api.__main__ import cpu_quota, default_workers
from handball_api.core.config import Settings
from handball_api.core.db import get_engine
from handball_api.core.errors import PROBLEM_MEDIA_TYPE
from handball_api.core.storage import MemoryStorage
from handball_api.main import create_app

from .conftest import _dsn


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://web.test"
    )


@pytest.fixture
async def refused_role(test_db: str) -> AsyncIterator[str]:
    """A login role the server refuses every connection to (CONNECTION LIMIT 0)."""
    name = f"hb_refused_{uuid.uuid4().hex[:8]}"
    conn = await asyncpg.connect(_dsn(test_db))
    await conn.execute(f"CREATE ROLE {name} LOGIN PASSWORD 'x' CONNECTION LIMIT 0")
    yield name
    await conn.execute(f"DROP ROLE IF EXISTS {name}")
    await conn.close()


async def test_a_refused_connection_answers_503(
    db_settings: Settings, refused_role: str, test_db: str
) -> None:
    url = _dsn(test_db, refused_role, "x").replace("postgresql://", "postgresql+asyncpg://")
    app = create_app(db_settings.model_copy(update={"database_url": url}), storage=MemoryStorage())
    async with app.router.lifespan_context(app), await _client(app) as c:
        with capture_logs() as logs:
            # a session token: the API has to read the database to resolve it
            r = await c.get("/v1/me", headers={"authorization": "Bearer some-token"})
    assert r.status_code == 503, r.text
    assert r.headers["content-type"] == PROBLEM_MEDIA_TYPE
    assert r.headers["retry-after"] == "2"
    body = r.json()
    assert body["type"].endswith(":database-unavailable")
    assert body["request_id"] == r.headers["x-request-id"]
    assert "too many connections" not in r.text  # no server details to the client
    logged = [e for e in logs if e["event"] == "unhandled_exception"]
    assert len(logged) == 1
    assert logged[0]["kind"] == "database-unavailable" and logged[0]["status"] == 503


async def test_a_full_pool_answers_503_after_the_pool_timeout(db_settings: Settings) -> None:
    settings = db_settings.model_copy(
        update={"db_pool_size": 1, "db_max_overflow": 0, "db_pool_timeout_s": 0.2}
    )
    app = create_app(settings, storage=MemoryStorage())
    async with app.router.lifespan_context(app):
        async with get_engine().connect(), await _client(app) as c:  # holds the one connection
            r = await c.get("/v1/me", headers={"authorization": "Bearer some-token"})
        assert r.status_code == 503, r.text
        assert r.json()["type"].endswith(":database-unavailable")
        # with the connection back, the same request is answered
        async with await _client(app) as c:
            again = await c.get("/v1/me", headers={"authorization": "Bearer some-token"})
        assert again.status_code == 401


async def test_the_pool_is_sized_by_the_settings(db_settings: Settings) -> None:
    settings = db_settings.model_copy(update={"db_pool_size": 3, "db_max_overflow": 1})
    app = create_app(settings, storage=MemoryStorage())
    async with app.router.lifespan_context(app):
        pool = get_engine().pool
        assert pool.size() == 3  # type: ignore[attr-defined]
        assert pool._max_overflow == 1  # type: ignore[attr-defined]


def test_an_unexpected_error_stays_a_500(app: FastAPI) -> None:
    # only the database out of reach is a 503; a fault of the code stays a 500 (test_errors)
    from handball_api.core.db import database_unavailable

    assert not database_unavailable(RuntimeError("boom"))
    assert not database_unavailable(ValueError("bad"))


def test_workers_follow_the_cpu_quota_of_the_container(tmp_path: Path) -> None:
    v2 = tmp_path / "cpu.max"
    v2.write_text("50000 100000\n")  # half a core (Container Apps cpu = 0.5)
    assert cpu_quota(v2, tmp_path / "none", tmp_path / "none") == 0.5
    v2.write_text("max 100000\n")  # no limit
    assert cpu_quota(v2, tmp_path / "none", tmp_path / "none") is None
    quota, period = tmp_path / "cfs_quota_us", tmp_path / "cfs_period_us"
    quota.write_text("200000\n")
    period.write_text("100000\n")
    assert cpu_quota(tmp_path / "none", quota, period) == 2.0
    quota.write_text("-1\n")
    assert cpu_quota(tmp_path / "none", quota, period) is None
    # half a core: two processes (one may block on CPU work while the other answers), not the
    # host's core count; never more than four
    assert default_workers(0.5, 16) == 2
    assert default_workers(2.0, 16) == 2
    assert default_workers(3.0, 16) == 3
    assert default_workers(None, 16) == 4
    assert default_workers(None, 1) == 1

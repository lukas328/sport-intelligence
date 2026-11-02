from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path
from typing import Any

import asyncpg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import event

from handball_api.core.config import Settings
from handball_api.core.db import get_engine
from handball_api.core.email import MemoryEmailSender
from handball_api.core.ratelimit import MemoryRateLimiter
from handball_api.core.storage import MemoryStorage
from handball_api.main import create_app
from handball_api.routers.health import get_checks
from handball_api.services.health import Check

API_DIR = Path(__file__).resolve().parent.parent
ADMIN_DSN = os.environ.get(
    "HB_TEST_ADMIN_DSN", "postgresql://handball:handball@localhost:5432/postgres"
)
APP_PASSWORD = "handball_app"


# ---- health tests (no database) ------------------------------------------------------------


@pytest.fixture
def settings() -> Settings:
    return Settings(
        env="test",
        log_json=False,
        database_url="postgresql+asyncpg://x:y@127.0.0.1:1/z",
        email_backend="memory",
        rate_limit_backend="memory",
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings, storage=MemoryStorage())


@pytest.fixture
def override_checks(app: FastAPI) -> Callable[[dict[str, Check]], None]:
    def _set(checks: dict[str, Check]) -> None:
        app.dependency_overrides[get_checks] = lambda: checks

    return _set


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---- database-backed tests ----------------------------------------------------------------


def _dsn(db: str, user: str = "handball", password: str = "handball") -> str:
    base = ADMIN_DSN.split("://", 1)[1].split("@", 1)[1].rsplit("/", 1)[0]
    return f"postgresql://{user}:{password}@{base}/{db}"


@pytest.fixture(scope="session")
def test_db() -> Iterator[str]:
    """Fresh database per test session, migrated with Alembic as the owner role."""
    name = f"handball_test_{uuid.uuid4().hex[:8]}"

    async def setup() -> None:
        conn = await asyncpg.connect(ADMIN_DSN)
        try:
            await conn.execute(f'CREATE DATABASE "{name}"')
            exists = await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = 'handball_app'")
            if not exists:
                await conn.execute(
                    f"CREATE ROLE handball_app LOGIN PASSWORD '{APP_PASSWORD}' "
                    "NOSUPERUSER NOBYPASSRLS"
                )
        finally:
            await conn.close()

    try:
        asyncio.run(setup())
    except OSError as exc:  # pragma: no cover
        pytest.skip(f"Postgres not reachable ({exc}); run `docker compose up -d postgres`")
    env = {
        **os.environ,
        "HB_MIGRATION_DATABASE_URL": _dsn(name).replace("postgresql://", "postgresql+asyncpg://"),
    }
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=API_DIR,
        env=env,
        check=True,
        capture_output=True,
    )
    yield name

    async def teardown() -> None:
        conn = await asyncpg.connect(ADMIN_DSN)
        try:
            await conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        finally:
            await conn.close()

    asyncio.run(teardown())


TABLES = (
    "audit_logs, consents, invitations, roster_entries, players, memberships, seasons, teams, "
    "org_memberships, organizations, auth_tokens, auth_sessions, users"
)


@pytest.fixture
async def owner_conn(test_db: str) -> AsyncIterator[asyncpg.Connection]:
    conn = await asyncpg.connect(_dsn(test_db))
    yield conn
    await conn.close()


@pytest.fixture
async def clean_db(owner_conn: asyncpg.Connection) -> AsyncIterator[None]:
    yield
    await owner_conn.execute(f"TRUNCATE {TABLES} CASCADE")


@pytest.fixture
def db_settings(test_db: str) -> Settings:
    return Settings(
        env="test",
        log_json=False,
        database_url=_dsn(test_db, "handball_app", APP_PASSWORD).replace(
            "postgresql://", "postgresql+asyncpg://"
        ),
        email_backend="memory",
        rate_limit_backend="memory",
        web_base_url="http://web.test",
        cors_origins=["http://web.test"],
    )


@pytest.fixture
async def db_app(db_settings: Settings, clean_db: None) -> AsyncIterator[FastAPI]:
    app = create_app(
        db_settings,
        email=MemoryEmailSender(),
        storage=MemoryStorage(),
        rate_limiter=MemoryRateLimiter(),
    )
    async with app.router.lifespan_context(app):
        yield app


class Api:
    """Test client for one browser: keeps cookies and sends the CSRF header like the web app."""

    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self.http = AsyncClient(transport=ASGITransport(app=app), base_url="http://web.test")
        self.user: dict[str, Any] = {}

    def _headers(self, extra: dict[str, str] | None) -> dict[str, str]:
        headers = dict(extra or {})
        csrf = self.http.cookies.get("hb_csrf")
        if csrf and "x-csrf-token" not in headers:
            headers["x-csrf-token"] = csrf
        return headers

    async def get(self, url: str, **kw: Any) -> Response:
        return await self.http.get(url, **kw)

    async def post(self, url: str, headers: dict[str, str] | None = None, **kw: Any) -> Response:
        return await self.http.post(url, headers=self._headers(headers), **kw)

    async def put(self, url: str, headers: dict[str, str] | None = None, **kw: Any) -> Response:
        return await self.http.put(url, headers=self._headers(headers), **kw)

    async def patch(self, url: str, headers: dict[str, str] | None = None, **kw: Any) -> Response:
        return await self.http.patch(url, headers=self._headers(headers), **kw)

    async def delete(self, url: str, headers: dict[str, str] | None = None, **kw: Any) -> Response:
        return await self.http.delete(url, headers=self._headers(headers), **kw)

    async def register(
        self,
        email: str,
        name: str = "Test User",
        password: str = "correct-horse-1",
        invitation_token: str | None = None,
    ) -> Response:
        r = await self.post(
            "/v1/auth/register",
            json={
                "email": email,
                "name": name,
                "password": password,
                "accept_terms": True,
                "invitation_token": invitation_token,
            },
        )
        if r.status_code == 201:
            self.user = (await self.get("/v1/me")).json()
        return r

    async def close(self) -> None:
        await self.http.aclose()


@pytest.fixture
async def make_api(db_app: FastAPI) -> AsyncIterator[Callable[[], Api]]:
    clients: list[Api] = []

    def _make() -> Api:
        api = Api(db_app)
        clients.append(api)
        return api

    yield _make
    for c in clients:
        await c.close()


@pytest.fixture
def outbox(db_app: FastAPI) -> MemoryEmailSender:
    sender: MemoryEmailSender = db_app.state.email
    return sender


@pytest.fixture
def query_counter(db_app: FastAPI) -> Iterator[list[str]]:
    statements: list[str] = []

    def _count(conn: Any, cursor: Any, statement: str, *args: Any) -> None:
        if not statement.lstrip().upper().startswith("SELECT SET_CONFIG"):
            statements.append(statement)

    engine = get_engine().sync_engine
    event.listen(engine, "before_cursor_execute", _count)
    yield statements
    event.remove(engine, "before_cursor_execute", _count)


async def setup_club(
    api: Api, email: str = "coach@hc-test.ch", youth: bool = False
) -> dict[str, Any]:
    """Register, create org and team. Returns ids."""
    assert (await api.register(email, name="Coach Carter")).status_code == 201
    org = (await api.post("/v1/orgs", json={"name": "HC Test", "primary_color": "#112233"})).json()
    team = (
        await api.post(
            f"/v1/orgs/{org['id']}/teams",
            json={"name": "Herren 1", "gender": "men", "is_youth": youth},
        )
    ).json()
    return {
        "org": org["id"],
        "team": team["id"],
        "season": team["current_season"]["id"],
        "team_obj": team,
    }

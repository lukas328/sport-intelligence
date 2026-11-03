from __future__ import annotations

import asyncio
from collections.abc import Callable

from httpx import AsyncClient

from handball_api.services.health import Check


async def _ok() -> None:
    return None


async def _fail() -> None:
    raise ConnectionError("down")


async def _slow() -> None:
    await asyncio.sleep(5)


async def test_healthz(client: AsyncClient) -> None:
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.headers["x-request-id"]


async def test_request_id_is_propagated(client: AsyncClient) -> None:
    r = await client.get("/healthz", headers={"x-request-id": "abc123"})
    assert r.headers["x-request-id"] == "abc123"
    assert r.headers["x-content-type-options"] == "nosniff"


async def test_readyz_ok(
    client: AsyncClient, override_checks: Callable[[dict[str, Check]], None]
) -> None:
    override_checks({"database": _ok, "redis": _ok, "storage": _ok})
    r = await client.get("/readyz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert {c["name"] for c in body["components"]} == {"database", "redis", "storage"}


async def test_readyz_degraded(
    client: AsyncClient, override_checks: Callable[[dict[str, Check]], None]
) -> None:
    override_checks({"database": _ok, "redis": _fail})
    r = await client.get("/readyz")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    redis = next(c for c in body["components"] if c["name"] == "redis")
    assert redis == {
        "name": "redis",
        "status": "error",
        "latency_ms": redis["latency_ms"],
        "error": "ConnectionError",
    }


async def test_readyz_timeout(
    client: AsyncClient,
    override_checks: Callable[[dict[str, Check]], None],
) -> None:
    override_checks({"database": _slow})
    r = await client.get("/v1/health")
    assert r.status_code == 503
    assert r.json()["components"][0]["error"] == "TimeoutError"


async def test_default_checks_fail_without_services(client: AsyncClient) -> None:
    # no overrides: real checks against unreachable services must not crash the endpoint
    r = await client.get("/readyz")
    assert r.status_code == 503


async def test_security_headers(client: AsyncClient) -> None:
    r = await client.get("/healthz")
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "strict-transport-security" not in r.headers  # only with secure cookies (HTTPS)


async def test_hsts_with_secure_cookies() -> None:
    from httpx import ASGITransport

    from handball_api.core.config import Settings
    from handball_api.main import create_app

    app = create_app(Settings(cookie_secure=True))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/healthz")
    assert r.headers["strict-transport-security"].startswith("max-age=63072000")

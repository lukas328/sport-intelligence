from __future__ import annotations

from fastapi import FastAPI, Query
from httpx import ASGITransport, AsyncClient

from handball_api.core.errors import PROBLEM_MEDIA_TYPE, ProblemError


def _register(app: FastAPI) -> None:
    @app.get("/_test/problem")
    async def problem() -> None:
        raise ProblemError(409, "conflict-test", "already exists")

    @app.get("/_test/crash")
    async def crash() -> None:
        raise RuntimeError("boom")

    @app.get("/_test/validate")
    async def validate(n: int = Query()) -> int:
        return n


async def test_problem_error(app: FastAPI, client: AsyncClient) -> None:
    _register(app)
    r = await client.get("/_test/problem")
    assert r.status_code == 409
    assert r.headers["content-type"] == PROBLEM_MEDIA_TYPE
    body = r.json()
    assert body["type"].endswith(":conflict-test")
    assert body["title"] == "Conflict"
    assert body["detail"] == "already exists"
    assert body["instance"] == "/_test/problem"


async def test_not_found_is_problem(client: AsyncClient) -> None:
    r = await client.get("/nope")
    assert r.status_code == 404
    assert r.headers["content-type"] == PROBLEM_MEDIA_TYPE
    assert r.json()["title"] == "Not Found"


async def test_validation_error_is_problem(app: FastAPI, client: AsyncClient) -> None:
    _register(app)
    r = await client.get("/_test/validate", params={"n": "x"})
    assert r.status_code == 422
    body = r.json()
    assert body["type"].endswith(":validation-error")
    assert body["errors"][0]["loc"] == ["query", "n"]


async def test_unhandled_error_hides_details(app: FastAPI) -> None:
    _register(app)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as c:
        r = await c.get("/_test/crash")
    assert r.status_code == 500
    assert "boom" not in r.text

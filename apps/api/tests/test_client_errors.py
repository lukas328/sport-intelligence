"""Errors of the web app from the browser (routers/client_errors): written as one log line,
nothing personal (ids, e-mail addresses, the query of URLs masked again here), no cookie or CSRF
token needed, at most 30 per address in ten minutes, more dropped silently."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient
from structlog.testing import capture_logs

from handball_api.routers.client_errors import mask, mask_route

ID = "4a9f2d24-f32c-42b7-9d1b-9a86a6c6ffd5"


def body(**over: Any) -> dict[str, Any]:
    return {
        "kind": "react",
        "code": 418,
        "message": "Minified React error #418; visit https://react.dev/errors/418?args[]=HTML",
        "stack": f"Error at https://app.example.test/_next/static/chunks/a.js?v=1:1:2 for {ID}",
        "route": f"/app/{ID}/matches/{ID}/check?shots=1",
        "build": "1df1ea0",
        "device": "phone",
        **over,
    }


async def test_a_client_error_is_logged_without_anything_personal(client: AsyncClient) -> None:
    with capture_logs() as logs:
        r = await client.post(
            "/v1/client-errors", json=body(message=f"bad {ID} for coach@hc-test.ch")
        )
    assert r.status_code == 204
    line = next(x for x in logs if x["event"] == "client_error")
    assert line["route"] == "/app/:id/matches/:id/check"
    assert line["message"] == "bad :id for [email]"
    assert ID not in line["stack"] and "?v=1" not in line["stack"]
    assert (line["kind"], line["code"], line["device"], line["build"]) == (
        "react",
        418,
        "phone",
        "1df1ea0",
    )


async def test_only_the_known_fields_in_their_bounds(client: AsyncClient) -> None:
    assert (await client.post("/v1/client-errors", json=body(device="fridge"))).status_code == 422
    assert (await client.post("/v1/client-errors", json=body(message="x" * 301))).status_code == 422
    assert (await client.post("/v1/client-errors", json=body(name="Mia Probst"))).status_code == 422


async def test_more_than_thirty_in_ten_minutes_are_dropped_quietly(client: AsyncClient) -> None:
    with capture_logs() as logs:
        for _ in range(35):
            assert (await client.post("/v1/client-errors", json=body())).status_code == 204
    assert sum(1 for x in logs if x["event"] == "client_error") == 30


def test_masking() -> None:
    assert mask_route("/app/123/teams/7/players#x") == "/app/:n/teams/:n/players"
    assert (
        mask(f"see https://a.test/p?token=abc and {ID.upper()}") == "see https://a.test/p and :id"
    )

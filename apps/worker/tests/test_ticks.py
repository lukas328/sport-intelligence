from __future__ import annotations

import httpx

from handball_worker.ticks import scouting_tick


def test_scouting_tick_posts_and_survives_errors() -> None:
    seen: list[httpx.Request] = []

    def ok(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"created": 2})

    assert scouting_tick(httpx.Client(transport=httpx.MockTransport(ok)), reschedule=False) == 2
    assert seen[0].url.path == "/internal/scouting/due"
    assert seen[0].headers["x-internal-token"]

    def down(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    assert scouting_tick(httpx.Client(transport=httpx.MockTransport(down)), reschedule=False) == 0

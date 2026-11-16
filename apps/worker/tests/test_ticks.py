from __future__ import annotations

import httpx

from handball_worker.ticks import scouting_tick, watchdog_tick


def test_scouting_tick_posts_and_survives_errors() -> None:
    seen: list[httpx.Request] = []

    def ok(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("dunning"):
            return httpx.Response(200, json={"reminders": 0, "dunning": 0, "lapsed": 0})
        if request.url.path.endswith("onboarding/run"):
            return httpx.Response(200, json={"sent": 1})
        if request.url.path.endswith("ops/tick"):
            return httpx.Response(
                200, json={"status": [], "retention": {"notified": 0, "purged": 0}}
            )
        return httpx.Response(200, json={"created": 2})

    assert scouting_tick(httpx.Client(transport=httpx.MockTransport(ok)), reschedule=False) == 2
    assert [r.url.path for r in seen] == [
        "/internal/scouting/due",
        "/internal/billing/dunning",
        "/internal/onboarding/run",
        "/internal/ops/tick",
        "/internal/official/sync",
    ]
    assert seen[0].headers["x-internal-token"]

    def down(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    assert scouting_tick(httpx.Client(transport=httpx.MockTransport(down)), reschedule=False) == 0


def test_watchdog_tick_posts_and_survives_errors() -> None:
    seen: list[str] = []

    def ok(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json={"restarted": 1, "failed": 0})

    client = httpx.Client(transport=httpx.MockTransport(ok))
    assert watchdog_tick(client, reschedule=False) == {"restarted": 1, "failed": 0}
    assert seen == ["/internal/watchdog"]

    def down(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    assert watchdog_tick(httpx.Client(transport=httpx.MockTransport(down)), reschedule=False) == {}

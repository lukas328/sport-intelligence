"""Job progress reports to the API: retries, throttling, terminal updates that must arrive."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from handball_jobkit.reporter import Reporter, ReportError, clicked_points


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    slept: list[float] = []
    monkeypatch.setattr(time, "sleep", slept.append)
    return slept


def make(answer: Callable[[httpx.Request], httpx.Response]) -> tuple[Reporter, list[Any]]:
    posts: list[Any] = []

    def handler(request: httpx.Request) -> httpx.Response:
        posts.append(json.loads(request.content))
        return answer(request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return Reporter("http://api/", "secret", "job-1", {"a": 1, "b": 3}, client=client), posts


def test_reports_progress_and_result(sleeps: list[float]) -> None:
    rep, posts = make(lambda r: httpx.Response(200))
    rep.stage("a")
    rep.fraction(0.5)  # throttled: right after the stage update
    rep.stage("b")
    rep.succeed({"ok": True})
    assert [p["status"] for p in posts] == ["running", "running", "succeeded"]
    assert posts[1]["progress"] == 0.25 and posts[-1]["result"] == {"ok": True}
    assert posts[-1]["stages"]["b"]["status"] == "done"
    assert rep.url == "http://api/internal/jobs/job-1" and sleeps == []


def test_retries_without_sleeping_after_the_last_attempt(sleeps: list[float]) -> None:
    answers = iter([500, 502, 200])
    rep, posts = make(lambda r: httpx.Response(next(answers)))
    rep.succeed({})
    assert len(posts) == 3 and sleeps == [1, 3]


def test_terminal_update_raises_when_the_api_is_unreachable(sleeps: list[float]) -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    rep, _ = make(down)
    rep.stage("a")  # progress: gives up quietly
    rep.fraction(1.0)  # throttled, not sent
    with pytest.raises(ReportError, match=r"succeeded.*connection refused"):
        rep.succeed({})
    with pytest.raises(ReportError, match="failed"):
        rep.fail("boom")
    assert sleeps == [1, 3] * 3  # three attempts each, no sleep after the last one


def test_client_errors_are_not_retried(sleeps: list[float]) -> None:
    rep, posts = make(lambda r: httpx.Response(404))
    rep.fail("x" * 5000)
    assert len(posts) == 1 and len(posts[0]["error"]) == 4000 and sleeps == []


def test_persistent_server_errors_raise_for_terminal_updates(sleeps: list[float]) -> None:
    rep, posts = make(lambda r: httpx.Response(503))
    with pytest.raises(ReportError, match="HTTP 503"):
        rep.fail("boom")
    assert len(posts) == 3


def test_heartbeat_while_a_stage_runs_and_none_after_the_end() -> None:
    posts: list[Any] = []

    def handler(request: httpx.Request) -> httpx.Response:
        posts.append(json.loads(request.content))
        return httpx.Response(200)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    rep = Reporter("http://api", "secret", "job-1", {"a": 1}, client=client, heartbeat_s=0.05)
    rep.stage("a")  # a long step without fractions (a download)
    deadline = time.monotonic() + 3
    while len(posts) < 3 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert len(posts) >= 3, "the reporter says it is still there"
    assert all(p["status"] == "running" and p["stage"] == "a" for p in posts)
    rep.succeed({})
    count = len(posts)
    time.sleep(0.2)
    assert len(posts) == count and posts[-1]["status"] == "succeeded"


def test_no_heartbeat_thread_without_interval() -> None:
    rep, _ = make(lambda r: httpx.Response(200))
    quiet = Reporter("http://api", "s", "j", {"a": 1}, client=rep.client, heartbeat_s=None)
    quiet.stage("a")
    assert quiet._beat is None


def test_shares_the_hall_image_and_reads_the_court_points_back(sleeps: list[float]) -> None:
    marked = {"points": [{"image": [1, 2], "court": [0, 0]}], "space": "panorama", "frame_ms": 0}

    def answer(r: httpx.Request) -> httpx.Response:
        body = json.loads(r.content)
        return httpx.Response(200, json={"court_points": marked if body["stage"] == "b" else None})

    rep, posts = make(answer)
    assert clicked_points(rep.stage("a")) is None
    view = {"camera": "fixed", "panorama": {"width": 1280, "height": 720}}
    rep.share(view)
    assert posts[-1]["view"] == view and posts[-1]["stage"] == "a"
    assert clicked_points(rep.stage("b")) == marked
    # an answer that is not JSON, or none at all (an older API), gives no points
    rep2, _ = make(lambda r: httpx.Response(200, text="ok"))
    assert rep2.stage("a") is None and clicked_points(None) is None
    assert clicked_points({"court_points": {"points": []}}) is None

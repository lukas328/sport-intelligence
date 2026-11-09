"""Job progress reports to the API: retries, throttling, terminal updates that must arrive."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from handball_jobkit.reporter import Reporter, ReportError


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

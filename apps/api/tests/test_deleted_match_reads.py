"""After a match is deleted, the views the web still polls for it (graphics, events, stats,
progress, checks ...) answer 404 problem+json, never 500, and no derived data of it stays."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from typing import Any

import asyncpg
import pytest
import structlog
from structlog.testing import capture_logs

from handball_api.core.errors import PROBLEM_MEDIA_TYPE
from handball_api.services import matches as matches_service

from .conftest import Api, setup_club
from .test_matches import new_match

ROUNDS = 4


def _match_reads(api: Api) -> list[tuple[str, dict[str, Any]]]:
    """Every GET of the API below one match, from the OpenAPI document (new ones are covered
    without touching this test)."""
    paths = api.app.openapi()["paths"]
    return [
        (p, ops["get"])
        for p, ops in paths.items()
        if "get" in ops and p.startswith("/v1/orgs/{org_id}/matches/{match_id}")
    ]


def _url(path: str, op: dict[str, Any], org: str, match_id: str) -> str:
    for param in op.get("parameters", []):
        if param["in"] != "path":
            continue
        name = param["name"]
        if name == "org_id":
            value = org
        elif name == "match_id":
            value = match_id
        elif param.get("schema", {}).get("type") == "integer":
            value = "1"
        else:
            value = str(uuid.uuid4())
        path = path.replace("{" + name + "}", value).replace("{" + name + ":path}", value)
    return path


async def test_every_view_of_a_deleted_match_is_not_found(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    # a demo match has events, stats, phases and graphics; a plain one has nothing yet
    demo = (await api.post(f"/v1/orgs/{org}/teams/{ids['team']}/demo-match")).json()
    plain = await new_match(api, ids)
    reads = _match_reads(api)
    assert len(reads) > 20
    for path in ("graphics", "events", "stats", "insights", "parts"):  # filled before deleting
        r = await api.get(f"/v1/orgs/{org}/matches/{demo['id']}/{path}")
        assert r.status_code == 200, (path, r.text)
    for m in (demo, plain):
        assert (await api.delete(f"/v1/orgs/{org}/matches/{m['id']}")).status_code == 204
    wrong = []
    for m in (demo, plain):
        for path, op in reads:
            r = await asyncio.wait_for(api.get(_url(path, op, org, m["id"])), 10)
            if r.status_code != 404 or r.headers["content-type"] != PROBLEM_MEDIA_TYPE:
                wrong.append((path, r.status_code, r.text[:200]))
    assert wrong == []
    # the team's own views still answer
    for path in ("matches", f"seasons/{ids['season']}/roster", f"seasons/{ids['season']}/stats"):
        r = await api.get(f"/v1/orgs/{org}/teams/{ids['team']}/{path}")
        assert r.status_code == 200, (path, r.text)


async def test_reads_while_the_match_is_deleted_never_fail(make_api: Callable[[], Api]) -> None:
    """The web keeps polling while the delete runs: every answer is the data or a 404."""
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    reads = [(p, op) for p, op in _match_reads(api) if not p.endswith("/stream")]
    for _ in range(ROUNDS):
        demo = (await api.post(f"/v1/orgs/{org}/teams/{ids['team']}/demo-match")).json()
        urls = [_url(p, op, org, demo["id"]) for p, op in reads]
        answers = await asyncio.gather(
            api.delete(f"/v1/orgs/{org}/matches/{demo['id']}"), *[api.get(u) for u in urls]
        )
        assert answers[0].status_code == 204
        failed = [
            (u, r.status_code)
            for u, r in zip(urls, answers[1:], strict=True)
            if r.status_code >= 500
        ]
        assert failed == []


async def test_deleting_a_match_removes_its_cached_statistics(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    demo = (await api.post(f"/v1/orgs/{org}/teams/{ids['team']}/demo-match")).json()
    for path in ("stats", "insights"):
        assert (await api.get(f"/v1/orgs/{org}/matches/{demo['id']}/{path}")).status_code == 200
    count = "SELECT count(*) FROM stats_cache WHERE scope_id = $1"
    assert await owner_conn.fetchval(count, uuid.UUID(demo["id"])) == 2
    assert (await api.delete(f"/v1/orgs/{org}/matches/{demo['id']}")).status_code == 204
    assert await owner_conn.fetchval(count, uuid.UUID(demo["id"])) == 0


async def test_other_requests_answer_while_a_big_match_is_deleted(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    """Production, 08:48 to 08:58: while the coach deleted a big match (its files take long to
    remove), the roster, notifications, playlists and views of other matches failed together.
    The delete held the row of the coach's sign-in session (its last-seen time) for its whole
    transaction; every other request of the coach waited for that row, the pools filled up and
    requests failed. Now the other requests answer at once."""
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    demo = (await api.post(f"/v1/orgs/{org}/teams/{ids['team']}/demo-match")).json()
    # the coach was last seen a while ago: the next request records the time again
    await owner_conn.execute("UPDATE auth_sessions SET last_seen_at = now() - interval '1 hour'")
    storage = api.app.state.storage
    removing, release = asyncio.Event(), asyncio.Event()
    delete_prefix = storage.delete_prefix
    demo_id = uuid.UUID(demo["id"])

    async def slow_delete_prefix(bucket: str, prefix: str) -> int:
        # the files go only once the rows are gone (committed)
        gone = await owner_conn.fetchval("SELECT count(*) FROM matches WHERE id = $1", demo_id)
        assert gone == 0
        removing.set()
        await release.wait()  # thousands of video segments
        return int(await delete_prefix(bucket, prefix))

    storage.delete_prefix = slow_delete_prefix
    deleting = asyncio.create_task(api.delete(f"/v1/orgs/{org}/matches/{demo['id']}"))
    try:
        await asyncio.wait_for(removing.wait(), 5)
        for path in (
            f"/v1/orgs/{org}/teams/{ids['team']}/seasons/{ids['season']}/roster",
            f"/v1/orgs/{org}/me/notifications",
            f"/v1/orgs/{org}/teams/{ids['team']}/playlists",
        ):
            r = await asyncio.wait_for(api.get(path), 3)
            assert r.status_code == 200, (path, r.text)
    finally:
        release.set()
        assert (await deleting).status_code == 204
    # the last-seen time is still recorded
    recent = "SELECT bool_and(last_seen_at > now() - interval '1 minute') FROM auth_sessions"
    assert await owner_conn.fetchval(recent) is True


async def test_storage_failing_after_the_delete_is_logged(
    make_api: Callable[[], Api], monkeypatch: pytest.MonkeyPatch
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)

    async def broken(bucket: str, prefix: str) -> int:
        raise ConnectionError("storage down")

    api.app.state.storage.delete_prefix = broken
    with capture_logs() as logs:
        # a fresh logger: the module's one may be cached from an earlier test
        monkeypatch.setattr(matches_service, "log", structlog.get_logger("handball_api.matches"))
        r = await api.delete(f"/v1/orgs/{org}/matches/{m['id']}")
    assert r.status_code == 204
    assert (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).status_code == 404
    left = [e for e in logs if e["event"] == "match_files_left"]
    assert left and left[0]["prefix"] == f"{org}/{m['id']}/"

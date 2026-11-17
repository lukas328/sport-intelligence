"""Prüfen with a budget (second round A6, A7): at most ten questions, the result decides how many
goals are asked, «Weiss nicht» and «Für dieses Spiel fertig» are kept, and an analysis that found
too little asks nothing and says why."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg
import pytest

from handball_api.core.jobs import MemoryJobQueue
from handball_api.models import Event, Match, VideoAsset
from handball_api.services import checks
from handball_api.services.progress import ABANDON_UPLOAD_S

from .conftest import Api, setup_club
from .test_goal_candidates import _cand
from .test_identity_sync import _finish, _ingest, _tracks
from .test_matches import new_match, upload

pytestmark = pytest.mark.usefixtures("clean_db")

# 30 moments 20 s apart (each its own goal moment), the stronger half at rate 1
MANY = {
    "template": "2026-11-05.1",
    "default_rate": 2,
    "rates": [1, 2, 4],
    "duration_s": 700.0,
    "play_s": 560.0,
    "no_play_ms": [[0, 20_000]],
    "candidates": [
        _cand(30_000 + i * 20_000, 1 if i % 2 else 2, score=1.0 + i / 100) for i in range(30)
    ],
}


async def _analysed(
    api: Api, ids: dict[str, Any], result: dict[str, Any] | None = None
) -> tuple[str, str, str]:
    m = await new_match(api, ids)
    vid = (await upload(api, ids, m["id"], b"v" * 100))["id"]
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    job = jobs.jobs[-1][2]
    body = result or {"tracks": _tracks(), "detector": "heuristic", "goal_candidates": MANY}
    await _finish(api, job, body)
    return m["id"], vid, job


async def _graphics(api: Api, org: str, match_id: str) -> dict[str, Any]:
    r = await api.get(f"/v1/orgs/{org}/matches/{match_id}/graphics")
    assert r.status_code == 200, r.text
    return dict(r.json())


async def _note(api: Api, org: str) -> dict[str, Any]:
    items = (await api.get(f"/v1/orgs/{org}/me/notifications")).json()["items"]
    return dict(next(n for n in items if n["kind"].startswith("analysis_")))


def test_goal_limit_follows_the_result() -> None:
    assert checks.goal_limit(None, 9) == 9  # no result: the budget alone
    assert checks.goal_limit(2, 9) == 3  # 1.5 x two goals without a place
    assert checks.goal_limit(10, 9) == 9  # never past the budget
    assert checks.goal_limit(0, 9) == 0  # every goal placed: none asked
    assert checks.goal_limit(3, -2) == 0


def test_goals_missing_counts_the_placed_goals_in_the_video() -> None:
    m = Match(score_own=20, score_opponent=10, period_s=1800, periods=2)

    def goal(t_ms: int | None, source: str = "goal_candidate", **attrs: Any) -> Event:
        return Event(type="shot", outcome="goal", source=source, t_ms=t_ms, attributes=attrs)

    goals = [
        goal(10_000),
        goal(20_000, "scoreboard_ocr"),
        goal(None, "official_report", video={"t_ms": 30_000}),  # a report goal pinned
        goal(None, "official_report"),  # no time yet: not placed
        goal(40_000, "heuristic"),  # a guess from a throw-off: not placed
        goal(5_000_000),  # outside a 10-minute clip
    ]
    assert checks.goals_missing(Match(period_s=1800, periods=2), goals, None) is None
    assert checks.goals_missing(m, goals, None) == 30 - 4
    # a 10-minute clip of a 60-minute match holds about a sixth of the goals
    assert checks.goals_missing(m, goals, 600_000) == 5 - 3


def test_little_found_names_the_reason() -> None:
    def asset(analysis: dict[str, Any]) -> VideoAsset:
        return VideoAsset(id=uuid.uuid4(), analysis=analysis)

    moving = {"needs_calibration": True, "calibration_info": {"reason": "camera_motion"}}
    assert checks.little_found(asset(moving), False) == "camera_motion"
    assert checks.little_found(asset(moving), True) is None  # a person set the court
    assert checks.little_found(asset({"needs_calibration": True}), None) == "court"
    odd = {"needs_calibration": True, "calibration_info": {"reason": "weird"}}
    assert checks.little_found(asset(odd), False) == "court"
    few = {"signals": {"detector_few_people": True}}
    assert checks.little_found(asset(few), True) == "few_people"
    # the fallback still found moments: the analysis saw the play, the moments are asked
    seen = {**few, "goal_candidates": {"goal_candidates": 12, "shot_candidates": 3}}
    assert checks.little_found(asset(seen), True) is None
    # the fallback detector still followed the players
    followed = {**few, "stats": {"tracks": 35}}
    assert checks.little_found(asset(followed), True) is None
    assert checks.little_found(asset({**few, "stats": {"tracks": 2}}), True) == "few_people"
    idle = {"signals": {"play_s": 40.0, "duration_s": 1200.0}}
    assert checks.little_found(asset(idle), True) == "no_play"
    played = {"signals": {"play_s": 900.0, "duration_s": 1200.0}}
    assert checks.little_found(asset(played), True) is None
    short = {"signals": {"play_s": 10.0, "duration_s": 40.0}}  # a short clip is not judged
    assert checks.little_found(asset(short), True) is None
    assert checks.little_found(None, None) is None


async def test_at_most_ten_questions_the_rest_behind_more(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    match_id, vid, _ = await _analysed(api, ids)
    g = await _graphics(api, org, match_id)
    kinds = [c["kind"] for c in g["checks"]]
    # the throw-off first, then nine goal moments: ten, the rest offered
    assert kinds[0] == "kickoff" and kinds.count("goal") == 9 and len(kinds) == 10
    assert len(g["more_checks"]) == 30 - 9
    assert g["notice"] is None and g["goals_missing"] is None and g["skipped"] == 0
    # the strongest moments (rate 1, the highest score) are the ones asked
    rows = {
        r["id"]: r
        for r in (await api.get(f"/v1/orgs/{org}/matches/{match_id}/goal-candidates")).json()[
            "candidates"
        ]
    }
    asked = [rows[c["id"]] for c in g["checks"] if c["kind"] == "goal"]
    assert all(r["rate"] == 1 for r in asked)
    assert [r["goal_ms"] for r in asked] == sorted(r["goal_ms"] for r in asked)
    # the bell counts the budget only, never the moments behind «Mehr prüfen»
    note = await _note(api, org)
    assert note["kind"] == "analysis_questions"
    assert note["params"]["questions"] == 10 and note["params"]["more_moments"] == 0
    # the worker's signals are kept with the analysis
    a = (await api.get(f"/v1/orgs/{org}/videos/{vid}/analysis")).json()
    assert a["status"] == "ready"
    assert g["files"] == [{"video_id": vid, "filename": "spiel.mp4", "state": "ready"}]


async def test_weiss_nicht_is_kept_and_does_not_pull_the_next(
    make_api: Callable[[], Api],
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    match_id, vid, _ = await _analysed(api, ids)
    base = f"/v1/orgs/{org}/matches/{match_id}"
    g = await _graphics(api, org, match_id)
    goal = next(c for c in g["checks"] if c["kind"] == "goal")
    r = await api.post(f"{base}/checks/skip", json={"kind": "goal", "id": goal["id"]})
    assert r.status_code == 204, r.text
    r = await api.post(f"{base}/checks/skip", json={"kind": "kickoff", "period": 1})
    assert r.status_code == 204, r.text
    g = await _graphics(api, org, match_id)
    asked = {c["id"] for c in g["checks"]}
    # never again in this round, waiting behind «Mehr prüfen»; no other moment moves up
    assert goal["id"] not in asked and goal["id"] in {c["id"] for c in g["more_checks"]}
    assert [c["kind"] for c in g["checks"]].count("goal") == 8
    assert all(c["kind"] != "kickoff" for c in g["checks"])
    assert any(c["kind"] == "kickoff" for c in g["more_checks"]) and g["skipped"] == 2
    row = next(
        r
        for r in (await api.get(f"{base}/goal-candidates")).json()["candidates"]
        if r["id"] == goal["id"]
    )
    assert row["status"] == "open" and row["skipped"] is True
    assert (await _note(api, org))["params"]["questions"] == 8
    # answered later from «Mehr prüfen»: an ordinary review
    r = await api.put(
        f"{base}/goal-candidates/{goal['id']}/review", json={"status": "confirmed", "side": "own"}
    )
    assert r.status_code == 200 and r.json()["status"] == "confirmed", r.text
    # wrong questions are refused
    r = await api.post(f"{base}/checks/skip", json={"kind": "goal", "id": str(uuid.uuid4())})
    assert r.status_code == 404
    r = await api.post(f"{base}/checks/skip", json={"kind": "kickoff"})
    assert r.status_code == 422
    # a new analysis is a new round: its court and its moments are asked afresh
    r = await api.post(f"{base}/checks/skip", json={"kind": "field", "id": vid})
    assert r.status_code == 204
    match = (await api.get(base)).json()
    assert f"field:{vid}" in match["report_extra"]["checks_skipped"]


async def test_skip_all_clears_the_bell(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    match_id, _, _ = await _analysed(api, ids)
    base = f"/v1/orgs/{org}/matches/{match_id}"
    assert (await _note(api, org))["params"]["questions"] == 10
    r = await api.post(f"{base}/checks/skip-all")
    assert r.status_code == 200, r.text
    assert r.json() == {"skipped": 10, "moments": 30}
    g = await _graphics(api, org, match_id)
    assert g["checks"] == [] and len(g["more_checks"]) == 31  # 30 moments and the throw-off
    note = await _note(api, org)
    assert note["kind"] == "analysis_checked" and note["read_at"] is not None
    assert (await api.get(f"/v1/orgs/{org}/me/notifications")).json()["unread"] == 0
    # another club cannot
    other = make_api()
    oid = await setup_club(other, "b@hc-test.ch")
    r = await other.post(f"/v1/orgs/{oid['org']}/matches/{match_id}/checks/skip-all")
    assert r.status_code == 404


async def test_the_result_decides_how_many_goals_are_asked(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    match_id, _, _ = await _analysed(api, ids)
    base = f"/v1/orgs/{org}/matches/{match_id}"
    r = await api.patch(base, json={"score_own": 1, "score_opponent": 1})
    assert r.status_code == 200, r.text
    g = await _graphics(api, org, match_id)
    goals = [c for c in g["checks"] if c["kind"] == "goal"]
    # two goals without a place in the video: three questions
    assert g["goals_missing"] == 2 and len(goals) == 3
    r = await api.put(
        f"{base}/goal-candidates/{goals[0]['id']}/review",
        json={"status": "confirmed", "side": "own"},
    )
    assert r.status_code == 200, r.text
    g = await _graphics(api, org, match_id)
    assert g["goals_missing"] == 1
    assert len([c for c in g["checks"] if c["kind"] == "goal"]) == 2
    r = await api.put(
        f"{base}/goal-candidates/{goals[1]['id']}/review",
        json={"status": "confirmed", "side": "opponent"},
    )
    g = await _graphics(api, org, match_id)
    # every goal of the result has its place: no goal is asked any more
    assert g["goals_missing"] == 0 and all(c["kind"] != "goal" for c in g["checks"])


async def test_a_goal_already_known_is_not_asked(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    match_id, _, _ = await _analysed(api, ids)
    base = f"/v1/orgs/{org}/matches/{match_id}"
    g = await _graphics(api, org, match_id)
    goal = next(c for c in g["checks"] if c["kind"] == "goal")
    # a goal marked by hand at that moment
    r = await api.post(
        f"{base}/events",
        json={"type": "shot", "side": "own", "outcome": "goal", "t_ms": goal["frame_ref"] + 1000},
    )
    assert r.status_code == 201, r.text
    g = await _graphics(api, org, match_id)
    assert goal["id"] not in {c["id"] for c in g["checks"] + g["more_checks"]}


@pytest.mark.parametrize(
    ("extra", "reason"),
    [
        (
            {"needs_calibration": True, "calibration_info": {"reason": "camera_motion"}},
            "camera_motion",
        ),
        ({"detector_few_people": True, "goal_candidates": None}, "few_people"),
        ({"goal_candidates": {**MANY, "play_s": 12.0}}, "no_play"),
    ],
)
async def test_found_little_asks_nothing_and_says_why(
    make_api: Callable[[], Api], extra: dict[str, Any], reason: str
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    result = {
        "tracks": [] if "needs_calibration" in extra else _tracks(),
        "detector": "model",
        "chunks": 0,
        "goal_candidates": MANY,
        **extra,
    }
    match_id, vid, _ = await _analysed(api, ids, result)
    g = await _graphics(api, org, match_id)
    # at most the court question stays (setting the corners is what helps)
    assert {c["kind"] for c in g["checks"]} <= {"field"}
    assert g["notice"] == {
        "reason": reason,
        "failed": False,
        "video_id": vid,
        "duration_s": None,
        "limit_s": None,
    }
    # the moments stay reachable behind «Mehr prüfen», never counted (none were found when the
    # detector saw almost nobody)
    moments = 0 if reason == "few_people" else 30
    assert len([c for c in g["more_checks"] if c["kind"] == "goal"]) == moments
    note = await _note(api, org)
    assert note["params"].get("questions", 0) == len(g["checks"])


async def test_a_failed_analysis_says_why_and_whether_to_try_again(
    make_api: Callable[[], Api],
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    vid = (await upload(api, ids, m["id"], b"v" * 100))["id"]
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    r = await api.http.post(
        f"/internal/jobs/{jobs.jobs[-1][2]}",
        headers=token,
        json={
            "status": "failed",
            "progress": 0.4,
            "error": "JobTimeoutException: Task exceeded maximum timeout value (21600 seconds)",
        },
    )
    assert r.status_code == 200, r.text
    g = await _graphics(api, org, m["id"])
    # the throw-off still helps marking by hand; no goal moment is asked
    assert g["analysis"] == "failed" and [c["kind"] for c in g["checks"]] == ["kickoff"]
    assert g["notice"]["reason"] == "timeout" and g["notice"]["failed"] is True
    assert g["notice"]["limit_s"] == 6 * 3600 and g["notice"]["video_id"] == vid
    detail = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).json()
    f = detail["progress"]["files"][0]
    # the same file would run out of time again: no «Analyse neu starten»
    assert (f["state"], f["error"], f["retry"], f["limit_s"]) == ("failed", "timeout", False, 21600)


async def test_a_long_silent_upload_is_given_up_and_can_be_removed(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    r = await api.post(
        f"/v1/orgs/{org}/matches/{m['id']}/videos",
        json={"filename": "moorfeld.mp4", "size_bytes": 3_000_000_000, "content_type": "video/mp4"},
    )
    assert r.status_code == 201, r.text
    vid = r.json()["video"]["id"] if "video" in r.json() else r.json()["id"]
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    # an hour of silence: still interrupted, the watchdog leaves it
    await owner_conn.execute(
        "UPDATE video_assets SET created_at = now() - interval '1 hour' WHERE id = $1",
        uuid.UUID(vid),
    )
    r = await api.http.post("/internal/watchdog", headers=token)
    assert r.json()["abandoned"] == 0
    # 18 hours without a new part: given up, shown as failed, and the yellow line goes
    since = datetime.now(UTC) - timedelta(seconds=ABANDON_UPLOAD_S * 3)
    await owner_conn.execute(
        "UPDATE video_assets SET created_at = $2 WHERE id = $1", uuid.UUID(vid), since
    )
    r = await api.http.post("/internal/watchdog", headers=token)
    assert r.json()["abandoned"] == 1
    detail = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).json()
    f = detail["progress"]["files"][0]
    assert (f["stage"], f["state"], f["error"], f["retry"]) == (
        "upload",
        "failed",
        "abandoned",
        False,
    )
    assert detail["status"] == "failed"
    progress = (await api.get(f"/v1/orgs/{org}/progress")).json()
    assert all(p["match_id"] != m["id"] or p["state"] != "interrupted" for p in progress)
    # removed: the match waits for a video again
    assert (await api.delete(f"/v1/orgs/{org}/videos/{vid}")).status_code == 204
    detail = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).json()
    assert detail["status"] == "scheduled" and detail["videos"] == []

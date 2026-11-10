from __future__ import annotations

from collections.abc import Callable
from typing import Any

from handball_api.core.jobs import MemoryJobQueue

from .conftest import Api, setup_club
from .test_matches import new_match, upload


async def ready_video(api: Api, ids: dict[str, Any], match_id: str) -> None:
    """Upload and a successful ingest: the match has a ready main video."""
    await upload(api, ids, match_id, b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    ingest = next(j for j in reversed(jobs.jobs) if j[1].endswith("run_ingest"))
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    r = await api.http.post(
        f"/internal/jobs/{ingest[2]}",
        headers=token,
        json={
            "status": "succeeded",
            "progress": 1,
            "result": {
                "proxy_key": ingest[3]["prefix"] + "proxy.mp4",
                "hls_prefix": ingest[3]["prefix"] + "hls/",
            },
        },
    )
    assert r.status_code < 300, r.text


async def opponent_goals(api: Api, org: str, match_id: str, wing: int, back: int) -> None:
    url = f"/v1/orgs/{org}/matches/{match_id}/events"
    for k, (x, y) in enumerate([(38.0, 1.5)] * wing + [(29.0, 10.0)] * back):
        body = {"type": "shot", "side": "opponent", "outcome": "goal", "x": x, "y": y}
        r = await api.post(url, json={**body, "t_ms": 10_000 * (k + 1)})
        assert r.status_code == 201, r.text


async def test_season_themes_from_two_matches_with_video(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    url = f"/v1/orgs/{org}/teams/{ids['team']}/seasons/{ids['season']}/themes"
    first = await new_match(api, ids, kickoff_at="2026-10-03T18:00:00+02:00")
    await ready_video(api, ids, first["id"])
    await opponent_goals(api, org, first["id"], wing=4, back=4)
    # one match with video says nothing yet
    r = await api.get(url)
    assert r.status_code == 200, r.text
    assert r.json()["matches_with_video"] == 1 and r.json()["themes"] == []

    second = await new_match(api, ids, kickoff_at="2026-10-10T18:00:00+02:00")
    await ready_video(api, ids, second["id"])
    await opponent_goals(api, org, second["id"], wing=3, back=5)
    # a match with events but no video does not count
    third = await new_match(api, ids, kickoff_at="2026-10-17T18:00:00+02:00")
    await opponent_goals(api, org, third["id"], wing=6, back=0)

    data = (await api.get(url)).json()
    assert data["matches_with_video"] == 2
    assert [m["match_id"] for m in data["matches"]] == [first["id"], second["id"]]
    assert len(data["themes"]) <= 3
    back = next(t for t in data["themes"] if t["id"] == "conceded_position_RM")
    assert (back["matches"], back["of"], back["kind"]) == (2, 2, "weakness")
    assert back["params"]["position"] == "RM"
    assert [p["value"] for p in back["per_match"]] == [0.5, 0.625]
    # the scenes are the opponent's goals from the back, in match order
    assert [len(p["scenes"]) for p in back["per_match"]] == [4, 5]
    assert back["per_match"][0]["scenes"][0]["t_ms"] == 50_000
    # every theme has a value or a gap per match with video, never a made-up number
    assert all(len(t["per_match"]) == 2 for t in data["themes"])

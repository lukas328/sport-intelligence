"""Automatic highlights (addendum 01, 4.3)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from handball_api.core.jobs import MemoryJobQueue

from .conftest import Api, setup_club
from .test_identity_sync import _finish, _ingest, _tracks
from .test_matches import new_match, upload

pytestmark = pytest.mark.usefixtures("clean_db")
REEL = "handball_worker.reels.run_highlight_reel"


async def _consent(api: Api, ids: dict[str, Any], player: str, kind: str) -> None:
    r = await api.post(
        f"/v1/orgs/{ids['org']}/teams/{ids['team']}/players/{player}/consents",
        json={
            "kind": kind,
            "given_by": "self",
            "given_by_name": "X",
            "given_at": "2026-10-01T10:00:00+02:00",
        },
    )
    assert r.status_code == 201, r.text


async def test_reels_selection_consent_rendering_and_sharing(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org, team = ids["org"], ids["team"]
    roster = f"/v1/orgs/{org}/teams/{team}/seasons/{ids['season']}/roster"
    lena = (
        await api.post(
            roster,
            json={"first_name": "Lena", "last_name": "M", "jersey_number": 7, "birth_year": 1998},
        )
    ).json()
    nina = (
        await api.post(
            roster,
            json={"first_name": "Nina", "last_name": "K", "jersey_number": 9, "birth_year": 1999},
        )
    ).json()
    await _consent(api, ids, lena["player_id"], "highlights_internal")
    m = await new_match(api, ids)
    ev = f"/v1/orgs/{org}/matches/{m['id']}/events"
    for i, who in enumerate([lena, lena, nina, lena, nina]):
        await api.post(
            ev,
            json={
                "type": "shot",
                "side": "own",
                "outcome": "goal",
                "t_ms": 30_000 * (i + 1),
                "player_id": who["player_id"],
            },
        )
    await api.post(
        ev, json={"type": "steal", "side": "own", "t_ms": 200_000, "player_id": lena["player_id"]}
    )
    await api.post(
        ev, json={"type": "shot", "side": "opponent", "outcome": "goal", "t_ms": 210_000}
    )  # never a highlight

    await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    await _finish(api, jobs.jobs[-1][2], {"tracks": _tracks(), "detector": "heuristic"})
    reels = [j for j in jobs.jobs if j[1] == REEL]
    # team reel 16:9 and 9:16 plus Lena's reel; Nina has no consent and is left out
    assert len(reels) == 3
    team_reel = reels[0][3]["payload"]
    assert [c["label"] for c in team_reel["clips"]] == ["#7 Lena"] * 4
    assert team_reel["format"] == "16x9" and reels[1][3]["payload"]["format"] == "9x16"
    assert team_reel["intro"][0] == "HC Test"
    listed = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/highlights")).json()
    assert len(listed) == 3 and listed[0]["consent"]["excluded_players"] == [nina["player_id"]]
    assert {r["status"] for r in listed} == {"queued"}
    assert (
        await api.post(
            f"/v1/orgs/{org}/matches/{m['id']}/highlights", json={"player_id": nina["player_id"]}
        )
    ).status_code == 422

    reel = next(r for r in listed if r["player_id"] is None and r["format"] == "16x9")
    payload = next(j[3]["payload"] for j in reels if j[3]["payload"]["reel_id"] == reel["id"])
    await api.app.state.storage.put(
        api.app.state.settings.s3_bucket_artifacts, payload["out_key"], b"mp4", "video/mp4"
    )
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    done = await api.post(
        f"/internal/highlights/{reel['id']}",
        json={"status": "ready", "key": payload["out_key"]},
        headers=token,
    )
    assert done.status_code == 204
    assert (await api.get(f"/v1/orgs/{org}/highlights/{reel['id']}/video.mp4")).content == b"mp4"

    links = f"/v1/orgs/{org}/teams/{team}/share-links"
    blocked = await api.post(links, json={"kind": "highlight", "target_id": reel["id"]})
    assert blocked.status_code == 403 and blocked.json()["type"].endswith("consent-missing")
    await _consent(api, ids, lena["player_id"], "highlights_public")
    shared = await api.post(links, json={"kind": "highlight", "target_id": reel["id"]})
    assert shared.status_code == 201
    anon = make_api()
    assert (await anon.get(f"/v1/share/{shared.json()['token']}")).json()["highlight"][
        "scenes"
    ] == 4
    assert (await anon.get(f"/v1/share/{shared.json()['token']}/reel.mp4")).content == b"mp4"

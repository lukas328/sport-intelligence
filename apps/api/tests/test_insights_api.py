"""Insights, summaries and season stats (M7)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import asyncpg
import pytest

from handball_api.core.text import numbers_ok

from .conftest import Api, setup_club
from .test_matches import new_match

pytestmark = pytest.mark.usefixtures("clean_db")


class FakeText:
    model = "fake-model"

    def __init__(self, text: str | None) -> None:
        self.text = text
        self.facts: list[dict[str, Any]] = []

    async def summarise(self, facts: dict[str, Any]) -> str | None:
        self.facts.append(facts)
        return self.text


async def tagged_match(api: Api, ids: dict[str, Any], goals: int, misses: int, **kw: Any) -> str:
    m = await new_match(api, ids, **kw)
    url = f"/v1/orgs/{ids['org']}/matches/{m['id']}/events"
    for i in range(goals + misses):
        body = {
            "type": "shot",
            "side": "own",
            "outcome": "goal" if i < goals else "miss",
            "clock_s": 60 * i + 5,
            "x": 31.0,
            "y": 10.0,
        }
        assert (await api.post(url, json=body)).status_code == 201
    for i in range(6):
        body = {"type": "shot", "side": "opponent", "outcome": "goal", "clock_s": 60 * i + 30}
        await api.post(url, json=body)
    return str(m["id"])


def test_numbers_ok() -> None:
    assert numbers_ok("Wurfquote 29 % statt 60 %, 8 von 28 Würfen.", {29, 60, 8, 28})
    assert not numbers_ok("Wurfquote 31 %.", {29})
    assert numbers_ok("Zwei Punkte: 1 Tor und 2 Paraden.", set())
    assert numbers_ok("xG 2,5", {2.5})


async def test_insights_summary_and_season(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    await tagged_match(api, ids, 15, 10, kickoff_at="2026-09-05T18:00:00+02:00")
    await tagged_match(api, ids, 16, 9, kickoff_at="2026-09-12T18:00:00+02:00")
    bad = await tagged_match(api, ids, 8, 20, kickoff_at="2026-09-19T18:00:00+02:00")
    empty = (await new_match(api, ids))["id"]

    data = (await api.get(f"/v1/orgs/{org}/matches/{bad}/insights")).json()
    assert data["baseline_matches"] == 2
    ins = {i["id"]: i for i in data["insights"]}
    assert ins["shooting"]["params"]["value"] == 29
    assert data["summary"] is None
    assert (await api.get(f"/v1/orgs/{org}/matches/{empty}/insights")).json()["insights"] == []

    # summaries: not configured, rejected numbers, accepted text
    url = f"/v1/orgs/{org}/matches/{bad}/summary"
    api.app.state.text = None
    assert (await api.post(url)).status_code == 503
    api.app.state.text = FakeText("Die Wurfquote lag bei 31 %.")
    r = await api.post(url)
    assert r.status_code == 502 and r.json()["type"].endswith("summary-rejected")
    fake = FakeText(
        "Nur 8 von 28 Würfen sassen (29 %, sonst 62 %). Abschluss aus dem Rückraum üben."
    )
    api.app.state.text = fake
    try:
        r = await api.post(url)
        assert r.status_code == 200, r.text
        assert r.json()["model"] == "fake-model"
        facts = fake.facts[-1]
        assert "player_id" not in str(facts)
        assert facts["erkenntnisse"][0]["regel"]
        again = (await api.get(f"/v1/orgs/{org}/matches/{bad}/insights")).json()
        assert again["summary"]["text"].startswith("Nur 8 von 28")
        assert (await api.post(f"/v1/orgs/{org}/matches/{empty}/summary")).status_code == 409
    finally:
        api.app.state.text = None

    season = (
        await api.get(f"/v1/orgs/{org}/teams/{ids['team']}/seasons/{ids['season']}/stats")
    ).json()
    assert [m["goals"] for m in season["matches"]] == [15, 16, 8]
    assert season["totals"]["matches"] == 3
    assert season["totals"]["goals"] == 39
    assert season["totals"]["shooting_pct"] == pytest.approx(39 / 78, abs=1e-4)
    assert season["matches"][0]["opponent"] == "TV Gegner"

    opp_id = (await api.get(f"/v1/orgs/{org}/matches/{bad}")).json()["opponent"]["id"]
    prof = (await api.get(f"/v1/orgs/{org}/opponents/{opp_id}/profile")).json()
    assert prof["opponent"]["name"] == "TV Gegner"
    assert prof["tagged_matches"] == 3
    assert prof["totals"]["goals"] == 18
    assert len(prof["matches"]) == 4  # incl. the match without events
    missing = "00000000-0000-0000-0000-000000000009"
    assert (await api.get(f"/v1/orgs/{org}/opponents/{missing}/profile")).status_code == 404


async def test_youth_season_has_no_ranking(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api, youth=True)
    roster = f"/v1/orgs/{ids['org']}/teams/{ids['team']}/seasons/{ids['season']}/roster"
    a = (
        await api.post(roster, json={"first_name": "A", "last_name": "A", "jersey_number": 3})
    ).json()
    b = (
        await api.post(roster, json={"first_name": "B", "last_name": "B", "jersey_number": 9})
    ).json()
    m = await new_match(api, ids)
    url = f"/v1/orgs/{ids['org']}/matches/{m['id']}/events"
    for i, pid in enumerate([a["player_id"], b["player_id"], b["player_id"], b["player_id"]]):
        body = {
            "type": "shot",
            "side": "own",
            "outcome": "goal",
            "clock_s": 30 * i + 5,
            "player_id": pid,
        }
        assert (await api.post(url, json=body)).status_code == 201
    season = (
        await api.get(f"/v1/orgs/{ids['org']}/teams/{ids['team']}/seasons/{ids['season']}/stats")
    ).json()
    assert season["ranked"] is False
    assert [p["player_id"] for p in season["players"]] == [a["player_id"], b["player_id"]]


async def test_season_counts_every_played_match_and_each_goal_once(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    # played, the result is known, nothing tagged
    played = (await new_match(api, ids, kickoff_at="2026-09-05T18:00:00+02:00"))["id"]
    r = await api.patch(
        f"/v1/orgs/{org}/matches/{played}", json={"score_own": 27, "score_opponent": 25}
    )
    assert r.status_code == 200, r.text
    # tagged by the coach and the same three goals in the imported official report
    both = await tagged_match(api, ids, 3, 1, kickoff_at="2026-09-12T18:00:00+02:00", is_home=False)
    url = f"/v1/orgs/{org}/matches/{both}/events"
    for clock in (8, 68, 128):
        body = {"type": "shot", "side": "own", "outcome": "goal", "clock_s": clock}
        assert (await api.post(url, json=body)).status_code == 201
    await owner_conn.execute(
        "UPDATE events SET source = 'official_report' WHERE match_id = $1 AND x IS NULL",
        uuid.UUID(both),
    )
    await new_match(api, ids)  # not played yet: no result, no events

    season = (
        await api.get(f"/v1/orgs/{org}/teams/{ids['team']}/seasons/{ids['season']}/stats")
    ).json()
    rows = {m["match_id"]: m for m in season["matches"]}
    assert season["totals"]["matches"] == 2
    assert rows[played]["goals"] == 27 and rows[played]["tagged"] is False
    assert rows[both]["goals"] == 3 and rows[both]["score_opponent"] == 6
    assert season["totals"]["goals"] == 30
    # shooting and xG only from the tagged match; the official goals took over the positions
    assert season["totals"]["tagged_matches"] == 1
    assert season["totals"]["shooting_pct"] == 0.75
    assert season["totals"]["xg_coverage"] == 1.0
    assert rows[both]["xg_coverage"] == 1.0

    opp_id = (await api.get(f"/v1/orgs/{org}/matches/{both}")).json()["opponent"]["id"]
    prof = (await api.get(f"/v1/orgs/{org}/opponents/{opp_id}/profile")).json()
    home = {m["match_id"]: m["is_home"] for m in prof["matches"]}
    assert home[both] is False and home[played] is True

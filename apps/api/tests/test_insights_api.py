"""Insights, summaries and season stats (M7)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

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

"""Training tips from the analysis (K21)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from handball_api.services.drills import library
from handball_api.services.training_tips import drills_for, rank

from .conftest import Api, setup_club
from .test_insights_api import tagged_match

pytestmark = pytest.mark.usefixtures("clean_db")


def _weak(ident: str, key: str, score: float, **params: Any) -> dict[str, Any]:
    return {
        "id": ident,
        "kind": "weakness",
        "key": key,
        "params": params,
        "score": score,
        "sample": 11,
        "evidence": {"side": "own", "type": "shot"},
    }


def test_rank_prefers_what_comes_back() -> None:
    wings = _weak("zone_wing_left", "insights.zone_weak", 0.4, zone="wing_left", k=3, n=11)
    seven = _weak("seven_m", "insights.seven_m_low", 0.9, k=1, n=5)
    turnovers = _weak("turnovers", "insights.turnovers_high", 0.5, value=17)
    strength = {**wings, "id": "s", "kind": "strength"}
    player = _weak("player_7", "insights.player_inefficient", 1.0, number=7)
    ranked = rank(
        [
            ("m3", [seven, strength, player]),
            ("m2", [wings, turnovers]),
            ("m1", [wings]),
        ]
    )
    # the wing weakness came up twice; the 7 m one only once, but in the latest match
    assert [t["id"] for t in ranked] == ["zone_wing_left", "seven_m", "turnovers"]
    first = ranked[0]
    assert first["matches"] == 2 and first["match_id"] == "m2" and first["topics"] == ["wings"]
    assert first["drills"] and all(
        "wings" in next(d for d in library() if d["id"] == i)["focus"] for i in first["drills"]
    )
    assert ranked[1]["topics"] == ["seven_m"]


def test_drills_for_a_topic_start_with_basic_ones() -> None:
    ids = drills_for(["goalkeeping"])
    assert len(ids) == 3
    by_id = {d["id"]: d for d in library()}
    assert by_id[ids[0]]["focus"][0] == "goalkeeping" and by_id[ids[0]]["level"] == "basic"
    assert drills_for(["unknown"]) == []


async def test_training_tips(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    url = f"/v1/orgs/{ids['org']}/teams/{ids['team']}/training-tips"
    # nothing analysed yet: an honest empty answer
    empty = (await api.get(url)).json()
    assert empty == {"matches_analysed": 0, "plan_required": False, "matches": [], "tips": []}

    await tagged_match(api, ids, 15, 10, kickoff_at="2026-09-05T18:00:00+02:00")
    await tagged_match(api, ids, 16, 9, kickoff_at="2026-09-12T18:00:00+02:00")
    bad = await tagged_match(api, ids, 8, 20, kickoff_at="2026-09-19T18:00:00+02:00")
    data = (await api.get(url)).json()
    assert data["matches_analysed"] == 3 and data["matches"][0]["match_id"] == bad
    tips = {t["id"]: t for t in data["tips"]}
    shooting = tips["shooting"]
    assert shooting["match_id"] == bad and shooting["of"] == 3 and shooting["matches"] == 1
    assert shooting["topics"] == ["finishing"] and shooting["metric"] == "shooting_pct"
    assert shooting["params"]["value"] == 29
    assert len(shooting["drills"]) == 3
    assert len(data["tips"]) <= 3

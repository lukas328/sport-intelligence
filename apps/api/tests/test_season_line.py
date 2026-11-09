"""A player's season line: figures per match with the events behind them, as the match
statistics count them (one source per goal)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest

from handball_api.core.email import MemoryEmailSender

from .conftest import Api, setup_club
from .test_matches import new_match
from .test_roster import _join, roster_url

pytestmark = pytest.mark.usefixtures("clean_db")


async def _event(api: Api, org: str, match: str, **body: Any) -> str:
    r = await api.post(f"/v1/orgs/{org}/matches/{match}/events", json=body)
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


async def test_season_line(
    make_api: Callable[[], Api], outbox: MemoryEmailSender, owner_conn: Any
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    org = ids["org"]
    add = roster_url(ids)
    lena = (
        await coach.post(
            add, json={"first_name": "Lena", "last_name": "Muster", "jersey_number": 9}
        )
    ).json()
    mia = (
        await coach.post(add, json={"first_name": "Mia", "last_name": "Probst", "jersey_number": 1})
    ).json()
    nora = (await coach.post(add, json={"first_name": "Nora", "last_name": "Beispiel"})).json()
    lp, gk = lena["player_id"], mia["player_id"]

    # match 1: tagged, and the first goal also in the imported official report
    m1 = (await new_match(coach, ids, kickoff_at="2026-09-05T18:00:00+02:00"))["id"]
    tagged_goal = await _event(
        coach, org, m1, type="shot", side="own", outcome="goal", clock_s=8, player_id=lp
    )
    official_goal = await _event(
        coach, org, m1, type="shot", side="own", outcome="goal", clock_s=10
    )
    await owner_conn.execute(
        "UPDATE events SET source = 'official_report' WHERE id = $1", uuid.UUID(official_goal)
    )
    seven = await _event(
        coach,
        org,
        m1,
        type="shot",
        side="own",
        outcome="goal",
        clock_s=300,
        player_id=lp,
        shot_type="penalty",
        assist_player_id=nora["player_id"],
    )
    miss = await _event(
        coach, org, m1, type="shot", side="own", outcome="miss", clock_s=400, player_id=lp
    )
    blocked = await _event(
        coach, org, m1, type="shot", side="own", outcome="blocked", clock_s=450, player_id=lp
    )
    fault = await _event(
        coach,
        org,
        m1,
        type="turnover",
        side="own",
        clock_s=500,
        player_id=lp,
        turnover_type="steps",
    )
    two_min = await _event(
        coach, org, m1, type="suspension_2min", side="own", clock_s=600, player_id=lp
    )
    yellow = await _event(coach, org, m1, type="yellow_card", side="own", clock_s=200, player_id=lp)
    keeper = {"goalkeeper_id": gk}
    save = await _event(
        coach, org, m1, type="shot", side="opponent", outcome="save", clock_s=700, attributes=keeper
    )
    against = await _event(
        coach, org, m1, type="shot", side="opponent", outcome="goal", clock_s=800, attributes=keeper
    )
    r = await coach.patch(
        f"/v1/orgs/{org}/matches/{m1}", json={"score_own": 2, "score_opponent": 1}
    )
    assert r.status_code == 200
    r = await coach.put(
        f"/v1/orgs/{org}/attendance/match/{m1}",
        json={"records": [{"player_id": lp, "status": "present"}]},
    )
    assert r.status_code == 200, r.text
    # match 2: only the result is known
    m2 = (await new_match(coach, ids, kickoff_at="2026-09-12T18:00:00+02:00"))["id"]
    r = await coach.patch(
        f"/v1/orgs/{org}/matches/{m2}", json={"score_own": 20, "score_opponent": 25}
    )
    assert r.status_code == 200
    await new_match(coach, ids)  # not played: not in the line

    base = f"/v1/orgs/{org}/teams/{ids['team']}/seasons/{ids['season']}/players"
    r = await coach.get(f"{base}/{lp}/line")
    assert r.status_code == 200, r.text
    line = r.json()
    assert line["first_name"] == "Lena" and line["jersey_number"] == 9
    assert [m["match_id"] for m in line["matches"]] == [m1, m2]
    one, two = line["matches"]
    assert one["opponent"] == "TV Gegner" and one["result"] == "win"
    assert (one["score_own"], one["score_opponent"]) == (2, 1)
    assert one["tagged"] and one["involved"] and one["attendance"] == "present"
    assert two["result"] == "loss" and not two["tagged"] and not two["involved"]
    assert two["attendance"] is None and all(v == 0 for v in two["figures"].values())

    f, ev = one["figures"], one["events"]
    # the tagged goal and the official one are one goal: it counts once, by the official id
    assert ev["goals"] == [official_goal, seven] and tagged_goal not in ev["goals"]
    assert f["goals"] == 2 and f["shots"] == 3 and f["blocked"] == 1 and f["misses"] == 1
    assert ev["misses"] == [miss] and ev["blocked"] == [blocked]
    assert ev["seven_m_goals"] == [seven] and ev["seven_m_shots"] == [seven]
    assert ev["turnovers"] == [fault] and ev["suspensions"] == [two_min]
    assert ev["yellow_cards"] == [yellow] and f["red_cards"] == 0
    assert one["shooting_pct"] == round(2 / 3, 4)
    for k, v in f.items():  # every figure links to as many events
        assert len(ev[k]) == v, k

    # the figures are those of the match statistics
    stats = (await coach.get(f"/v1/orgs/{org}/matches/{m1}/stats")).json()
    row = stats["players"][f"p:{lp}"]
    for k in ("goals", "shots", "misses", "blocked", "seven_m_goals", "turnovers", "suspensions"):
        assert f[k] == row[k], k
    assert stats["own"]["goals"] == 2

    # the goalkeeper: saves and goals against credited to her
    keeper_line = (await coach.get(f"{base}/{gk}/line")).json()
    kf, ke = keeper_line["matches"][0]["figures"], keeper_line["matches"][0]["events"]
    gk_row = stats["goalkeepers"][f"own:p:{gk}"]
    assert (kf["faced"], kf["saves"], kf["goals_against"]) == (2, 1, 1)
    assert (gk_row["faced"], gk_row["saves"]) == (2, 1)
    assert ke["saves"] == [save] and ke["goals_against"] == [against]
    assert keeper_line["matches"][0]["save_pct"] == 0.5
    # the assist is Nora's
    nora_line = (await coach.get(f"{base}/{nora['player_id']}/line")).json()
    assert nora_line["matches"][0]["events"]["assists"] == [seven]

    totals = line["totals"]
    assert totals["matches"] == 2 and totals["tagged_matches"] == 1
    assert totals["matches_involved"] == 1 and totals["matches_present"] == 1
    assert totals["goals"] == 2 and totals["shots"] == 3 and totals["yellow_cards"] == 1
    assert totals["shooting_pct"] == round(2 / 3, 4) and totals["save_pct"] is None

    # players read their own line only; the staff every player of the team
    player = await _join(make_api, coach, ids, outbox, "lena@hc-test.ch", player_id=lp)
    analyst = await _join(make_api, coach, ids, outbox, "an@hc-test.ch", "analyst")
    assert (await player.get(f"{base}/{lp}/line")).status_code == 200
    r = await player.get(f"{base}/{gk}/line")
    assert r.status_code == 403
    assert (await analyst.get(f"{base}/{gk}/line")).json()["matches"][0]["figures"]["saves"] == 1

    # an entry from the official data without account or consent: only for the organisers
    await owner_conn.execute(
        "UPDATE roster_entries SET official_provider = 'handball_ch', official_player_id = 77 "
        "WHERE player_id = $1",
        uuid.UUID(nora["player_id"]),
    )
    assert (await analyst.get(f"{base}/{nora['player_id']}/line")).status_code == 404
    assert (await coach.get(f"{base}/{nora['player_id']}/line")).status_code == 200

    # unknown player or season, another club
    assert (await coach.get(f"{base}/{uuid.uuid4()}/line")).status_code == 404
    team = f"/v1/orgs/{org}/teams/{ids['team']}"
    assert (await coach.get(f"{team}/seasons/{uuid.uuid4()}/players/{lp}/line")).status_code == 404
    other = make_api()
    await setup_club(other, "other@hc-test.ch")
    assert (await other.get(f"{base}/{lp}/line")).status_code == 404

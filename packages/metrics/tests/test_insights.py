from __future__ import annotations

from typing import Any

import pytest

from handball_metrics import Event, EventType, Side, compute_match_stats
from handball_metrics.insights import match_insights, wilson

OWN, OPP = Side.OWN, Side.OPPONENT
_n = iter(range(100_000))


def shot(side: Side, outcome: str, clock: float = 0, **kw: Any) -> Event:
    return Event(
        id=f"e{next(_n)}", type=EventType.SHOT, side=side, outcome=outcome, clock_s=clock, **kw
    )


def match(
    own_goals: int, own_misses: int, opp_goals: int = 10, opp_saves: int = 10, **extra: list[Event]
) -> dict[str, Any]:
    ev = [shot(OWN, "goal", 60 * i + 1, x=31.0, y=10.0) for i in range(own_goals)]
    ev += [shot(OWN, "miss", 60 * i + 30, x=31.0, y=10.0) for i in range(own_misses)]
    ev += [shot(OPP, "goal", 60 * i + 15) for i in range(opp_goals)]
    ev += [shot(OPP, "save", 60 * i + 45) for i in range(opp_saves)]
    for more in extra.values():
        ev += more
    return compute_match_stats(ev)


def test_wilson() -> None:
    lo, hi = wilson(5, 10)
    assert lo < 0.5 < hi
    assert wilson(0, 0) == (0.0, 1.0)
    assert wilson(10, 10)[1] == pytest.approx(1.0)


def test_shooting_below_baseline_is_ranked_and_explained() -> None:
    base = [match(15, 10), match(16, 9), match(14, 11)]  # ~60 %
    bad = match(8, 20)  # 29 %
    ins = match_insights(bad, base)
    first = next(i for i in ins if i["id"] == "shooting")
    assert first["kind"] == "weakness"
    assert first["key"] == "insights.shooting_below"
    assert first["params"] == {"value": 29, "baseline": 60, "k": 8, "n": 28}
    assert first["evidence"] == {"side": "own", "type": "shot"}
    assert 29 in first["numbers"] and first["sample"] == 28


def test_no_insight_inside_the_interval_or_without_baseline() -> None:
    base = [match(15, 10), match(16, 9)]
    assert not [i for i in match_insights(match(14, 11), base) if i["id"] == "shooting"]
    assert not [i for i in match_insights(match(5, 25), [match(15, 10)]) if i["id"] == "shooting"]
    # too few shots
    assert not [i for i in match_insights(match(1, 5), base) if i["id"] == "shooting"]


def test_catalogue_rules() -> None:
    sevens = [shot(OWN, "miss", 100 + i, shot_type="penalty") for i in range(3)] + [
        shot(OWN, "goal", 200, shot_type="penalty")
    ]
    zone_left = [shot(OWN, "miss", 300 + i, x=34.0, y=1.0) for i in range(5)]
    conceded = [shot(OPP, "goal", 400 + i, goal_zone="TL") for i in range(6)]
    fast = [
        Event(
            id=f"f{i}",
            type=EventType.SHOT,
            side=OPP,
            outcome="goal",
            clock_s=500 + i,
            shot_zone="fast_break",
        )
        for i in range(4)
    ]
    run = [shot(OPP, "goal", 1500 + i) for i in range(5)]
    player = [shot(OWN, "goal", 2000 + i, player_id="p7") for i in range(6)] + [
        shot(OWN, "miss", 2100, player_id="p7")
    ]
    keeper = [
        shot(OPP, "save", 2200 + i, x=30.0, y=10.0, attributes={"goalkeeper_id": "gk"})
        for i in range(9)
    ]
    stats = match(
        8,
        6,
        opp_goals=3,
        opp_saves=0,
        a=sevens,
        b=zone_left,
        c=conceded,
        d=fast,
        e=run,
        f=player,
        g=keeper,
    )
    ids = {i["id"]: i for i in match_insights(stats, [], limit=20)}
    assert ids["seven_m"]["params"] == {"k": 1, "n": 4, "value": 25}
    assert ids["conceded_zone"]["params"]["zone"] == "TL"
    assert ids["fast_breaks_against"]["params"] == {"value": 4}
    assert ids["opponent_run"]["kind"] == "weakness"
    assert ids["player_good_p7"]["params"]["k"] == 6
    assert ids["keeper_gk"]["kind"] == "strength"
    assert any(k.startswith("zone_") for k in ids)
    # ranked by score, limited
    scores = [i["score"] for i in match_insights(stats, [], limit=3)]
    assert scores == sorted(scores, reverse=True) and len(scores) == 3


def test_turnovers_and_drought() -> None:
    base = [match(15, 10), match(15, 10)]
    tos = [
        Event(
            id=f"t{i}", type=EventType.TURNOVER, side=OWN, clock_s=10 + i, turnover_type="bad_pass"
        )
        for i in range(9)
    ]
    late = [shot(OWN, "goal", 1500)]  # 23 minutes after the previous own goal
    stats = match(3, 3, a=tos, b=late)
    ids = {i["id"]: i for i in match_insights(stats, base, limit=20)}
    assert ids["turnovers"]["params"]["type"] == "bad_pass"
    assert ids["drought"]["params"]["minutes"] >= 8


def test_keeper_is_not_judged_on_goals_with_positions_alone() -> None:
    """The demo case: positions came with the goals (overlay, tracking) but not with the saves.
    Over those shots xG is always below the goals, so a keeper with 44 % saves read as "14.8
    goals below expectation". Without positions for most saves and goals there is no GSAx and no
    keeper insight; with them, a good keeper is a strength."""
    gk = {"goalkeeper_id": "gk"}
    goals = [shot(OPP, "goal", 100 + i, x=34.0, y=10.0, attributes=gk) for i in range(19)]
    saves = [shot(OPP, "save", 200 + i, attributes=gk) for i in range(15)]
    stats = compute_match_stats(goals + saves)
    k = stats["goalkeepers"]["own:p:gk"]
    assert k["save_pct"] == pytest.approx(15 / 34, abs=1e-3)
    assert k["xg_shots"] == 19 and k["gsax"] is None
    assert not [i for i in match_insights(stats, [], limit=20) if i["id"].startswith("keeper")]

    saves = [shot(OPP, "save", 200 + i, x=34.0, y=10.0, attributes=gk) for i in range(15)]
    stats = compute_match_stats(goals + saves)
    k = stats["goalkeepers"]["own:p:gk"]
    assert k["gsax"] == pytest.approx(k["xg_against"] - 19, abs=0.01)
    assert k["gsax"] > 0  # 44 % saves on shots from 6 m: better than expected
    ids = {i["id"]: i for i in match_insights(stats, [], limit=20)}
    assert ids["keeper_gk"]["kind"] == "strength"

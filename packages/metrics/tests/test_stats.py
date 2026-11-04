from __future__ import annotations

import pytest

from handball_metrics import Event, EventType, Side, compute_match_stats, expected_goal
from handball_metrics.stats import situations, zone_of

OWN, OPP = Side.OWN, Side.OPPONENT


def shot(i: int, side: Side, outcome: str, clock: float, **kw: object) -> Event:
    return Event(id=f"s{i}", type=EventType.SHOT, side=side, outcome=outcome, clock_s=clock, **kw)  # type: ignore[arg-type]


def test_shooting_and_save_percentages() -> None:
    ev = [
        shot(1, OWN, "goal", 60, player_id="a", x=34.5, y=10.0),
        shot(
            2,
            OWN,
            "save",
            120,
            player_id="a",
            x=29.0,
            y=10.0,
            attributes={"goalkeeper_id": "gk-opp"},
        ),
        shot(3, OWN, "miss", 180, player_id="b"),
        shot(4, OWN, "post", 200, player_id="b"),
        shot(5, OWN, "blocked", 220, player_id="b"),
        shot(6, OPP, "goal", 240, number=7),
        shot(7, OPP, "save", 260, number=7, attributes={"goalkeeper_id": "gk-own"}),
        shot(8, OPP, "save", 280, number=9),
        shot(9, OPP, "miss", 300, number=9),
    ]
    s = compute_match_stats(ev, {"own": 10, "opponent": 9})
    own, opp = s["own"], s["opponent"]
    assert (own["goals"], own["shots"], own["shots_blocked"], own["posts"], own["misses"]) == (
        1,
        4,
        1,
        1,
        1,
    )
    assert own["shooting_pct"] == 0.25
    assert (own["saves"], own["goals_against"]) == (2, 1)
    assert own["save_pct"] == pytest.approx(2 / 3, abs=1e-4)
    assert own["attack_efficiency"] == 0.1
    assert opp["shooting_pct"] == 0.25  # 1 goal from 4 shots (goal, 2 saves, miss)
    assert own["zones"]["circle_centre"] == {"shots": 1, "goals": 1}
    assert s["players"]["p:a"]["goals"] == 1 and s["players"]["p:a"]["saved"] == 1
    assert s["players"]["opponent#7"]["shots"] == 2
    assert s["players"]["p:gk-own"]["saves"] == 1
    assert s["timeline"]["final"] == {"own": 1, "opp": 1}


def test_turnovers_sevens_suspensions_and_situations() -> None:
    ev = [
        Event(
            id="t1",
            type=EventType.TURNOVER,
            side=OWN,
            turnover_type="bad_pass",
            clock_s=10,
            player_id="a",
        ),
        Event(
            id="t2",
            type=EventType.TURNOVER,
            side=OWN,
            turnover_type="steps",
            clock_s=20,
            player_id="a",
        ),
        Event(id="p1", type=EventType.SUSPENSION, side=OPP, clock_s=100, number=5),
        shot(1, OWN, "goal", 150, shot_type="penalty", player_id="a"),
        Event(id="7", type=EventType.SEVEN_METER_AWARDED, side=OWN, clock_s=145),
        shot(
            2, OWN, "goal", 230, player_id="b", assist_player_id="a"
        ),  # after the suspension ended
        shot(3, OPP, "miss", 160, number=8),
    ]
    sit = situations(ev)
    assert sit["s1"] == "powerplay" and sit["s3"] == "shorthanded" and sit["s2"] == "equal"
    s = compute_match_stats(ev)
    own = s["own"]
    assert own["turnovers_by_type"] == {"bad_pass": 1, "steps": 1}
    assert (own["seven_m_awarded"], own["seven_m_shots"], own["seven_m_goals"]) == (1, 1, 1)
    assert own["by_situation"]["powerplay"] == {"shots": 1, "goals": 1, "pct": 1.0}
    assert s["opponent"]["suspensions"] == 1
    assert own["attack_efficiency"] is None  # possessions unknown
    a = s["players"]["p:a"]
    assert (a["turnovers"], a["assists"], a["seven_m_goals"]) == (2, 1, 1)


def test_runs_and_drought() -> None:
    goals = [(OWN, 60), (OPP, 200), (OPP, 300), (OPP, 420), (OWN, 900), (OWN, 960)]
    ev = [shot(i, side, "goal", t) for i, (side, t) in enumerate(goals)]
    tl = compute_match_stats(ev)["timeline"]
    assert tl["best_run"]["opponent"] == {"goals": 3, "from_s": 200}
    assert tl["best_run"]["own"]["goals"] == 2
    assert tl["longest_own_drought_s"] == {"seconds": 840.0, "from_s": 60, "to_s": 900}
    assert [p["own"] for p in tl["score"]] == [0, 1, 1, 1, 1, 2, 3]


def test_zone_and_quality() -> None:
    assert zone_of(Event(id="x", type=EventType.SHOT, side=OWN, x=38.0, y=18.5)) == "wing_left"
    assert zone_of(Event(id="x", type=EventType.SHOT, side=OWN, shot_type="penalty")) == "penalty"
    assert zone_of(Event(id="x", type=EventType.SHOT, side=OWN)) is None
    s = compute_match_stats([shot(1, OWN, "goal", 1, confidence=0.4, source="heuristic")])
    assert s["quality"] == {"events": 1, "low_confidence": 1, "sources": {"heuristic": 1}}


def test_xg_prior() -> None:
    assert expected_goal(33, 10, "penalty") == 0.75
    assert expected_goal(None, None) == 0.5
    assert expected_goal(34.5, 10) > expected_goal(29, 10) > expected_goal(20, 10)
    assert expected_goal(30, 12, "fast_break") > expected_goal(30, 12)
    assert 0.3 < expected_goal(38, 18.5) < 0.55


def test_events_without_clock() -> None:
    ev = [
        shot(1, OWN, "goal", 0),
        Event(id="n", type=EventType.SHOT, side=OWN, outcome="goal", t_ms=5000),
    ]
    s = compute_match_stats(ev)
    assert s["timeline"]["final"] == {"own": 2, "opp": 0}
    assert situations(ev)["n"] == "unknown"


def test_goalkeepers() -> None:
    mine = {"goalkeeper_id": "gk1"}
    ev = [
        shot(1, OPP, "save", 10, x=31.0, y=10.0, goal_zone="TL", attributes=mine),
        shot(2, OPP, "goal", 20, x=31.0, y=10.0, goal_zone="TL", attributes=mine),
        shot(3, OPP, "save", 30, shot_type="penalty", attributes=mine),
        shot(4, OPP, "miss", 40, attributes=mine),  # not on target
        shot(5, OPP, "goal", 50, attributes={"goalkeeper_number": 12}),
        shot(6, OPP, "goal", 60),
        shot(7, OWN, "save", 70, attributes={"goalkeeper_number": 1}),
    ]
    gk = compute_match_stats(ev)["goalkeepers"]
    k = gk["own:p:gk1"]
    assert (k["faced"], k["saves"], k["goals_against"]) == (3, 2, 1)
    assert k["save_pct"] == pytest.approx(2 / 3, abs=1e-3)
    assert k["seven_m"] == {"faced": 1, "saves": 1}
    assert k["goal_zones"]["TL"] == {"faced": 2, "saves": 1}
    assert k["shot_zones"]["penalty"] == {"faced": 1, "saves": 1}
    xg = 2 * expected_goal(31.0, 10.0) + 0.75
    assert k["xg_against"] == pytest.approx(xg, abs=0.01)
    assert k["gsax"] == pytest.approx(xg - 1, abs=0.01)
    assert gk["own:n:12"]["number"] == 12
    assert gk["own:unknown"]["goals_against"] == 1
    assert gk["opponent:n:1"]["side"] == "opponent"


def test_goals_only_have_no_shooting_ratios() -> None:
    """Goals read from a score overlay: no misses or saves recorded, so no shooting or save
    percentage (it would read 100 % and 0 %), but goals per attack work."""
    ev = [shot(i, OWN if i % 2 else OPP, "goal", 60 * i, source="scoreboard_ocr") for i in range(5)]
    st = compute_match_stats(ev, {"own": 4, "opponent": 5})
    assert st["own"]["goals"] == 2 and st["opponent"]["goals"] == 3
    assert st["own"]["shooting_pct"] is None and st["opponent"]["save_pct"] is None
    assert st["own"]["attack_efficiency"] == 0.5

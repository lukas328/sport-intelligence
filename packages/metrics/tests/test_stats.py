from __future__ import annotations

import pytest

from handball_metrics import Event, EventType, Side, compute_match_stats, expected_goal
from handball_metrics.stats import (
    LINE_KEYS,
    POSITIONS,
    player_event_ids,
    position_of_zone,
    situations,
    zone_of,
)

OWN, OPP = Side.OWN, Side.OPPONENT


def shot(i: int, side: Side, outcome: str, clock: float, **kw: object) -> Event:
    return Event(id=f"s{i}", type=EventType.SHOT, side=side, outcome=outcome, clock_s=clock, **kw)  # type: ignore[arg-type]


def xg(x: float, y: float, shot_type: str | None = None) -> float:
    v = expected_goal(x, y, shot_type)
    assert v is not None
    return v


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
    assert s["quality"] == {
        "events": 1,
        "attempts_known": False,
        "low_confidence": 1,
        "sources": {"heuristic": 1},
    }


def test_xg_prior() -> None:
    assert expected_goal(33, 10, "penalty") == 0.75
    assert xg(34.5, 10) > xg(29, 10) > xg(20, 10)
    assert xg(30, 12, "fast_break") > xg(30, 12)
    assert 0.3 < xg(38, 18.5) < 0.55


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
    xg_against = 2 * xg(31.0, 10.0) + 0.75
    assert k["xg_against"] == pytest.approx(xg_against, abs=0.01)
    assert k["gsax"] == pytest.approx(xg_against - 1, abs=0.01)
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


def test_xg_only_covers_shots_with_inputs() -> None:
    """Goals without a shot position (official report, score overlay) have no xG: they stay out
    of the sum, and the coverage says how many shots the xG figure covers."""
    ev = [
        shot(1, OWN, "goal", 60, x=34.5, y=10.0),
        shot(2, OWN, "save", 120, x=29.0, y=10.0),
        shot(3, OWN, "goal", 180, shot_type="penalty"),
        shot(4, OWN, "goal", 240, source="official_report"),
        shot(5, OWN, "miss", 300),
        shot(6, OWN, "blocked", 320, x=29.0, y=10.0),  # not a shot on target
    ]
    own = compute_match_stats(ev)["own"]
    assert own["xg"] == pytest.approx(xg(34.5, 10.0) + xg(29.0, 10.0) + 0.75, abs=0.01)
    assert own["xg_shots"] == 3
    assert own["xg_goals"] == 2  # the report goal has no position: not set against the xG
    assert own["xg_coverage"] == pytest.approx(3 / 5, abs=1e-4)
    assert expected_goal(None, None) is None
    assert compute_match_stats([])["own"]["xg_coverage"] is None


def test_goal_counted_once_from_report_and_tagging() -> None:
    """A goal in the official report and also tagged (or read from the overlay) is one goal:
    the official goal counts and takes over the tagged shot position."""
    ev = [
        shot(1, OWN, "goal", 300, source="official_report", number=7),
        shot(2, OWN, "goal", 600, source="official_report", number=9),
        shot(3, OPP, "goal", 900, source="official_report"),
        # tagged by the coach after the import, a few seconds off the minute of the report
        shot(4, OWN, "goal", 305, source="user_correction", x=34.5, y=10.0, player_id="p7"),
        shot(5, OWN, "goal", 590, source="scoreboard_ocr"),
        # an overlay goal the report does not have: a misreading unless the coach confirmed it
        shot(6, OPP, "goal", 1500, source="scoreboard_ocr"),
        shot(7, OPP, "goal", 1800, source="scoreboard_ocr", attributes={"review": "confirmed"}),
        # a goal tagged far from every official goal: a person entered it, it counts
        shot(8, OWN, "goal", 2400, source="user_correction"),
        shot(9, OWN, "miss", 700, source="user_correction", x=29.0, y=10.0),
    ]
    s = compute_match_stats(ev)
    assert s["own"]["goals"] == 3
    assert s["opponent"]["goals"] == 2
    assert s["timeline"]["final"] == {"own": 3, "opp": 2}
    assert s["own"]["zones"]["circle_centre"] == {"shots": 1, "goals": 1}  # position taken over
    assert s["players"]["p:p7"]["goals"] == 1
    assert "#7" not in str(s["players"].keys())


def test_long_range_and_empty_goal_are_separate_zones() -> None:
    far = {"x": 20.0, "y": 10.0}
    assert zone_of(Event(id="a", type=EventType.SHOT, side=OWN, **far)) == "long_range"  # type: ignore[arg-type]
    empty = Event(id="b", type=EventType.SHOT, side=OWN, shot_type="empty_net", **far)  # type: ignore[arg-type]
    assert zone_of(empty) == "empty_goal"
    # stored before the split: an empty-goal shot kept the merged zone
    old = Event(
        id="c", type=EventType.SHOT, side=OWN, shot_type="empty_net", shot_zone="long_range"
    )
    assert zone_of(old) == "empty_goal"


def test_player_event_ids_match_the_figures() -> None:
    ev = [
        shot(1, OWN, "goal", 8, player_id="a", source="user_correction"),
        # the same goal from the official report, without scorer: it takes over "a"
        shot(2, OWN, "goal", 10, source="official_report"),
        shot(3, OWN, "goal", 300, player_id="a", shot_type="penalty", assist_player_id="b"),
        shot(4, OWN, "miss", 400, player_id="a"),
        shot(5, OWN, "blocked", 450, player_id="a"),
        shot(6, OWN, "save", 460, player_id="a", shot_type="penalty"),
        Event(id="t1", type=EventType.TURNOVER, side=OWN, clock_s=500, player_id="a"),
        Event(id="p1", type=EventType.SUSPENSION, side=OWN, clock_s=600, player_id="a"),
        Event(id="y1", type=EventType.YELLOW, side=OWN, clock_s=200, player_id="a"),
        shot(7, OPP, "save", 700, attributes={"goalkeeper_id": "gk"}),
        shot(8, OPP, "goal", 800, attributes={"goalkeeper_id": "gk"}, shot_type="penalty"),
    ]
    stats = compute_match_stats(ev)
    ids = player_event_ids(ev, "a")
    assert set(ids) == set(LINE_KEYS)
    assert ids["goals"] == ["s2", "s3"]  # in clock order, by the official goal's id
    assert ids["shots"] == ["s2", "s3", "s4", "s6"] and ids["blocked"] == ["s5"]
    assert ids["seven_m_shots"] == ["s3", "s6"] and ids["seven_m_goals"] == ["s3"]
    assert ids["yellow_cards"] == ["y1"]
    row = stats["players"]["p:a"]
    for k in ("goals", "shots", "misses", "saved", "blocked", "turnovers", "suspensions"):
        assert len(ids[k]) == row[k], k
    assert len(ids["seven_m_goals"]) == row["seven_m_goals"]
    assert len(ids["seven_m_shots"]) == row["seven_m_shots"]
    assert player_event_ids(ev, "b")["assists"] == ["s3"]
    assert stats["players"]["p:b"]["assists"] == 1
    keeper = player_event_ids(ev, "gk")
    gk = stats["goalkeepers"]["own:p:gk"]
    assert keeper["saves"] == ["s7"] and keeper["goals_against"] == ["s8"]
    assert len(keeper["faced"]) == gk["faced"] and len(keeper["saves"]) == gk["saves"]
    assert len(keeper["seven_m_faced"]) == gk["seven_m"]["faced"] == 1


def test_goals_conceded_by_position() -> None:
    """Six positions (LA, RL, RM, RR, RA, KM) from the shot zones; 7 m and fast breaks are none."""
    assert position_of_zone("wing_left") == "LA"
    assert position_of_zone("half_right") == "RR"
    assert position_of_zone("circle_centre") == "KM"
    assert position_of_zone("penalty") is None
    events = [
        shot(1, OPP, "goal", 60, x=38.0, y=18.5),  # left wing
        shot(2, OPP, "goal", 120, x=38.0, y=1.5),  # right wing
        shot(3, OPP, "save", 180, x=38.0, y=1.5),
        shot(4, OPP, "goal", 240, x=34.5, y=10.0),  # pivot, 5.5 m
        shot(5, OPP, "goal", 300, shot_type="penalty"),
        shot(6, OWN, "goal", 360, x=38.0, y=18.5),
    ]
    s = compute_match_stats(events)
    conceded = s["opponent"]["positions"]
    assert tuple(conceded) == POSITIONS
    assert {p: v["goals"] for p, v in conceded.items()} == {
        "LA": 1,
        "RL": 0,
        "RM": 0,
        "RR": 0,
        "RA": 1,
        "KM": 1,
    }
    assert conceded["RA"] == {"shots": 2, "goals": 1, "zones": ["wing_right"]}
    # the penalty goal is in the total but has no position
    assert s["own"]["goals_against"] == 4
    assert s["own"]["positions"]["LA"]["goals"] == 1


def test_goals_without_time_have_no_runs_and_no_course() -> None:
    # a paper report: 29 own goals, no times; the order is unknown, so no "run of 29"
    ev = [Event(id=f"g{i}", type=EventType.SHOT, side=OWN, outcome="goal") for i in range(29)] + [
        Event(id=f"o{i}", type=EventType.SHOT, side=OPP, outcome="goal") for i in range(19)
    ]
    tl = compute_match_stats(ev)["timeline"]
    assert tl["timed"] is False
    assert tl["final"] == {"own": 29, "opp": 19}
    assert tl["best_run"]["own"]["goals"] == 0 and tl["best_run"]["opponent"]["goals"] == 0
    assert tl["longest_own_drought_s"]["seconds"] == 0
    assert len(tl["score"]) == 1


def test_ratios_need_attempts_in_their_own_direction() -> None:
    # our keeper's saves are recorded, our misses are not: our save % is known, our shooting % and
    # the opponent's save % are not (they would read 100 % and 0 %)
    ev = [
        shot(1, OWN, "goal", 60),
        shot(2, OPP, "goal", 120),
        shot(3, OPP, "save", 180),
    ]
    s = compute_match_stats(ev)
    assert s["own"]["save_pct"] == 0.5
    assert s["own"]["shooting_pct"] is None
    assert s["opponent"]["save_pct"] is None
    assert s["opponent"]["shooting_pct"] == 0.5
    assert s["own"]["known"] == {"shooting": False, "saving": True, "turnovers": False}

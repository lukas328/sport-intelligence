from __future__ import annotations

from typing import Any

from handball_metrics import Event, EventType, Side, compute_match_stats
from handball_metrics.themes import MatchInput, season_themes

OPP = Side.OPPONENT


def right_wing_goals(i: int, goals: int, others: int) -> list[Event]:
    """A match where the opponent scores `goals` from the right wing and `others` from the back."""
    events = [
        Event(
            id=f"{i}w{k}",
            type=EventType.SHOT,
            side=OPP,
            outcome="goal",
            clock_s=60.0 * k,
            x=38.0,
            y=1.5,
        )
        for k in range(goals)
    ]
    events += [
        Event(
            id=f"{i}b{k}",
            type=EventType.SHOT,
            side=OPP,
            outcome="goal",
            clock_s=900.0 + 60 * k,
            x=29.0,
            y=10.0,
        )
        for k in range(others)
    ]
    return events


def inp(i: int, stats: dict[str, Any], insights: list[dict[str, Any]] | None = None) -> MatchInput:
    return MatchInput(match_id=f"m{i}", stats=stats, insights=insights or [])


def test_nothing_before_two_matches_with_video() -> None:
    s = compute_match_stats(right_wing_goals(1, 5, 3))
    assert season_themes([inp(1, s)]) == []


def test_a_position_that_stays_open_is_a_theme_with_a_value_per_match() -> None:
    matches = [
        inp(1, compute_match_stats(right_wing_goals(1, 4, 5))),  # 4 of 9
        inp(2, compute_match_stats(right_wing_goals(2, 1, 8))),  # 1 of 9: does not fire
        inp(3, compute_match_stats(right_wing_goals(3, 5, 4))),  # 5 of 9
    ]
    themes = season_themes(matches)
    # the back (most goals in all three matches) comes before the right wing (two of three)
    assert [t["id"] for t in themes] == ["conceded_position_RM", "conceded_position_RA"]
    t = themes[1]
    assert (t["matches"], t["of"], t["kind"]) == (2, 3, "weakness")
    assert [p["fired"] for p in t["per_match"]] == [True, False, True]
    # the series has a value for every match, also where the theme did not fire
    assert [p["value"] for p in t["per_match"]] == [0.444, 0.111, 0.556]
    # the scenes: the opponent's goals from that position
    assert t["per_match"][0]["evidence"] == {
        "side": "opponent",
        "type": "shot",
        "outcome": "goal",
        "zones": ["wing_right"],
    }


def test_match_insights_that_repeat_and_ranking() -> None:
    s = compute_match_stats(right_wing_goals(1, 0, 3))
    weak = {
        "id": "seven_m",
        "kind": "weakness",
        "key": "insights.seven_m_low",
        "params": {"k": 1, "n": 4, "value": 25},
        "score": 0.6,
        "evidence": {"zone": "penalty"},
    }
    strong = {
        "id": "own_run",
        "kind": "strength",
        "key": "insights.own_run",
        "params": {"goals": 5},
        "score": 0.7,
        "evidence": {},
    }
    info = {"id": "note", "kind": "info", "key": "x", "params": {}, "score": 1.0, "evidence": {}}
    themes = season_themes(
        [inp(1, s, [weak, strong, info]), inp(2, s, [weak, strong, info]), inp(3, s, [strong])]
    )
    # three matches before two, then weaknesses first; info never becomes a theme
    assert [t["id"] for t in themes] == ["own_run", "seven_m"]
    assert themes[1]["matches"] == 2

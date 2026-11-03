from __future__ import annotations

import pytest

from handball_metrics import Event, EventType, Side
from handball_metrics.query import Filter, MatchInfo, Row, aggregate, compare, compute, select

OWN, OPP = Side.OWN, Side.OPPONENT
M1 = MatchInfo("m1", "2026-10-01", "TV Muster", 20, 18, opponent_formations=((0, 60_000, "5-1"),))
M2 = MatchInfo("m2", "2026-10-08", "HC Beispiel", 25, 27)
M3 = MatchInfo("m3", "2026-10-15", "TV Muster", 22, 22)


def ev(i: int, match: MatchInfo, type_: EventType, side: Side, clock: float, **kw: object) -> Row:
    e = Event(id=f"e{i}", type=type_, side=side, clock_s=clock, **kw)  # type: ignore[arg-type]
    return Row(e, match)


ROWS = [
    ev(1, M1, EventType.SHOT, OWN, 30, outcome="goal", x=38.0, y=18.5, number=7, t_ms=30_000),
    ev(2, M1, EventType.TIMEOUT, OWN, 100),
    ev(3, M1, EventType.SHOT, OWN, 150, outcome="save", x=29.0, y=10.0, number=7, t_ms=90_000),
    ev(4, M1, EventType.SHOT, OPP, 200, outcome="goal", x=37.0, y=1.0),
    ev(5, M1, EventType.SHOT, OWN, 400, outcome="goal", shot_type="penalty", number=9),
    ev(6, M2, EventType.SHOT, OWN, 60, outcome="miss", x=28.0, y=15.0, number=9),
    ev(7, M2, EventType.TURNOVER, OWN, 90, turnover_type="bad_pass"),
    ev(8, M2, EventType.SHOT, OPP, 120, outcome="save", x=37.0, y=1.0),
    ev(9, M3, EventType.SHOT, OWN, 1900, outcome="goal", shot_type="fast_break", period=2),
    ev(10, M3, EventType.SHOT, OPP, 2000, outcome="goal", x=34.5, y=10.0, period=2),
    ev(
        11,
        M3,
        EventType.SHOT,
        OWN,
        2100,
        outcome="goal",
        x=30,
        y=10,
        period=2,
        attributes={"play_id": "p1"},
    ),
]


def test_filters() -> None:
    assert len(select(ROWS, Filter(side="own", type="shot"))) == 6
    assert {r.match.id for r in select(ROWS, Filter(last_n_matches=1))} == {"m3"}
    assert {r.match.id for r in select(ROWS, Filter(opponent="muster"))} == {"m1", "m3"}
    assert [r.event.id for r in select(ROWS, Filter(zone="wing_right"))] == ["e4", "e8"]
    assert [r.event.id for r in select(ROWS, Filter(number=7))] == ["e1", "e3"]
    assert [r.event.id for r in select(ROWS, Filter(period=2, side="opponent"))] == ["e10"]
    assert [r.event.id for r in select(ROWS, Filter(minute_from=7))] == ["e5", "e9", "e10", "e11"]
    # up to 120 s after the own timeout at 100 s
    assert [r.event.id for r in select(ROWS, Filter(after_timeout_s=120))] == ["e3", "e4"]
    assert [r.event.id for r in select(ROWS, Filter(opponent_formation="5-1"))] == ["e1"]
    assert [r.event.id for r in select(ROWS, Filter(play_id="p1"))] == ["e11"]
    with pytest.raises(ValueError, match="unknown filter"):
        Filter.from_dict({"colour": "red"})
    assert Filter.from_dict({"side": "own", "zone": None, "match_ids": ["m1"]}).match_ids == ("m1",)


def test_metrics() -> None:
    own = select(ROWS, Filter(side="own"))
    v = compute("shooting_pct", own)
    assert (v.value, v.numerator, v.denominator, v.matches) == (0.667, 4.0, 6, 3)
    assert compute("seven_m_pct", own).value == 1.0
    assert compute("fast_break_goals", own).value == 1.0
    assert compute("turnovers", own).value == 1.0
    # our goalkeeper: saves of the opponent's shots on target
    keeper = compute("save_pct", select(ROWS, Filter(side="opponent")))
    assert (keeper.value, keeper.numerator, keeper.denominator) == (0.333, 1.0, 3)
    assert compute("shooting_pct", []).value is None
    xg = compute("xg", own)
    assert xg.value is not None and 2 < xg.value < 6 and xg.denominator == 6
    with pytest.raises(ValueError):
        compute("happiness", own)


def test_group_and_compare() -> None:
    own_shots = select(ROWS, Filter(side="own", type="shot"))
    by_number = aggregate(own_shots, "goals", "number")
    assert by_number["value"] == 4.0
    assert [(g["key"], g["value"]) for g in by_number["groups"]] == [("7", 1.0), ("9", 1.0)]
    by_match = aggregate(own_shots, "shooting_pct", "match")
    assert {g["key"]: g["value"] for g in by_match["groups"]} == {"m1": 0.667, "m2": 0.0, "m3": 1.0}
    minutes = aggregate(ROWS, "events", "minute_10")
    assert {g["key"] for g in minutes["groups"]} == {"1-10", "31-40"}
    c = compare(
        ROWS,
        "shooting_pct",
        Filter(side="own", opponent="muster"),
        Filter(side="own", opponent="beispiel"),
    )
    assert c["a"]["value"] == 0.8 and c["b"]["value"] == 0.0 and c["difference"] == 0.8
    assert "not proof" in c["note"]
    with pytest.raises(ValueError):
        aggregate(ROWS, "goals", "shoe_size")

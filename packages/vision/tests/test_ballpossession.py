"""Holder, possessions, passes and turnovers from a ball path and player boxes."""

from __future__ import annotations

from handball_vision import ballpossession as bp

FPS = 25.0
TEAMS = {1: "home", 2: "home", 3: "away", 4: "home_gk"}


def _box(tid: int, x: float, y: float = 300.0) -> bp.Box:
    return (tid, x - 20, y - 90, x + 20, y)


def test_holder_prefers_upper_body_and_ignores_far_balls() -> None:
    boxes = [_box(1, 100), _box(3, 130)]
    assert bp.holder((100, 240), boxes) == 1
    assert bp.holder((128, 230), boxes) == 3
    assert bp.holder((100, 196), boxes) == 1  # overhead
    assert bp.holder((400, 240), boxes) is None


def test_pass_then_interception() -> None:
    ball: dict[int, tuple[float, float]] = {}
    boxes: dict[int, list[bp.Box]] = {}
    for f in range(0, 150):
        boxes[f] = [_box(1, 100), _box(2, 500), _box(3, 800)]
        if f < 30:
            ball[f] = (100, 240)  # player 1 holds
        elif f < 45:
            ball[f] = (100 + (f - 30) * 26, 150)  # in flight above the boxes
        elif f < 90:
            ball[f] = (500, 240)  # player 2 holds
        elif f < 100:
            ball[f] = (500 + (f - 90) * 30, 150)
        else:
            ball[f] = (800, 240)  # opponent 3 has it
        if f == 60:
            ball[f] = (100, 240)  # one wrong frame: not a possession
    by = bp.holders(ball, boxes)
    pos = bp.possessions(by, TEAMS, FPS)
    assert [(p.track_id, p.first, p.last) for p in pos] == [(1, 0, 29), (2, 45, 89), (3, 100, 149)]
    moves = bp.transfers(pos, FPS)
    assert [(m.kind, m.from_track, m.to_track) for m in moves] == [
        ("pass", 1, 2),
        ("turnover", 2, 3),
    ]
    s = bp.summary(pos, moves, FPS)
    assert s["passes"] == {"home": 1} and s["turnovers"] == {"home": 1}
    assert s["ball_time_s"] == {"home": 3.0, "away": 2.0}


def test_goalkeeper_pass_counts_for_the_team() -> None:
    pos = [bp.Possession(4, "home_gk", 0, 20), bp.Possession(1, "home", 40, 60)]
    assert [m.kind for m in bp.transfers(pos, FPS)] == ["pass"]


def test_long_loss_is_not_a_pass() -> None:
    pos = [bp.Possession(1, "home", 0, 20), bp.Possession(2, "home", 200, 260)]
    assert bp.transfers(pos, FPS) == []

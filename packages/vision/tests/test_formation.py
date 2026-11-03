from __future__ import annotations

import numpy as np

from handball_vision.formation import Sample, classify, detect, summary

DEFENCE = {
    "6-0": [(33.5, 2.5), (33.4, 6), (33.6, 8.8), (33.5, 11.2), (33.4, 14), (33.5, 17.5)],
    "5-1": [(33.5, 2.5), (33.4, 6.5), (33.6, 10), (33.4, 13.5), (33.5, 17.5), (30.5, 10)],
    "3-2-1": [(33.5, 3), (33.6, 10), (33.5, 17), (31.2, 6.5), (31.2, 13.5), (28.5, 10)],
}
ATTACK = [(37, 1.5), (29.5, 5), (29, 10), (29.5, 15), (37, 18.5), (33.8, 9)]


def frames(formation: str, start_ms: int, seconds: float, seed: int = 0) -> list[Sample]:
    """Home defends the right goal in `formation`, away attacks; 25 fps with small jitter."""
    rng = np.random.default_rng(seed)
    out = []
    for f in range(int(seconds * 25)):
        t = start_ms + f * 40
        for i, (x, y) in enumerate(DEFENCE[formation]):
            out.append(Sample(t, i + 1, "home", x + rng.normal(0, 0.3), y + rng.normal(0, 0.3)))
        out.append(Sample(t, 20, "home_gk", 39.2, 10))
        for i, (x, y) in enumerate(ATTACK):
            out.append(Sample(t, 30 + i, "away", x + rng.normal(0, 0.4), y + rng.normal(0, 0.4)))
        out.append(Sample(t, 40, "away_gk", 1.0, 10))
        out.append(Sample(t, 50, "referee", 25, 3))
    return out


def test_classify_rules() -> None:
    assert classify([6.5] * 6) == "6-0"
    assert classify([6.5] * 5 + [9]) == "5-1"
    assert classify([6.5] * 4 + [9, 9]) == "4-2"
    assert classify([6.5] * 3 + [8.8, 8.8, 11]) == "3-2-1"
    assert classify([6.5] * 3 + [9, 9, 9]) == "3-3"
    assert classify([6.5, 6.5, 12, 12, 12, 12]) == "open"


def test_detects_segments_and_switch() -> None:
    samples = (
        frames("6-0", 0, 20)
        + frames("5-1", 20_000, 16, seed=1)
        + frames("3-2-1", 36_000, 12, seed=2)
    )
    segs = detect(samples)
    home = [(s.formation, s.start_ms, s.end_ms) for s in segs if s.team == "home"]
    assert [h[0] for h in home] == ["6-0", "5-1", "3-2-1"]
    assert home[0][1] == 0 and abs(home[1][1] - 20_000) <= 2000
    assert all(s.confidence > 0.8 for s in segs if s.team == "home")
    # the away team is attacking, never in a set defence
    assert not [s for s in segs if s.team == "away"]
    per = summary(segs)["home"]
    assert per["6-0"] >= 18_000 and per["5-1"] >= 12_000


def test_transition_and_mirror() -> None:
    # everybody in the middle: no set defence
    mid = [Sample(t, i, "home", 20 + i, 10) for t in range(0, 10_000, 40) for i in range(6)]
    assert detect(mid) == []
    assert detect([]) == []
    # mirrored: home defends the left goal, no goalkeeper track
    mirrored = [
        Sample(s.t_ms, s.track, s.team, 40 - s.x, 20 - s.y)
        for s in frames("5-1", 0, 10)
        if s.team in ("home", "away")
    ]
    segs = detect(mirrored)
    assert [s.formation for s in segs if s.team == "home"] == ["5-1"]

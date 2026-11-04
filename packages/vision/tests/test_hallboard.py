"""Hall scoreboard: parsing text tokens, goals per side from noisy, partial readings."""

from __future__ import annotations

from handball_vision import hallboard as hb


def _tk(text: str, x: float, y: float = 330.0, w: float = 30.0, h: float = 20.0) -> hb.Token:
    return hb.Token(text, x, y, x + w, y + h, 0.95)


def test_parse_full_and_cut_board() -> None:
    full = [_tk("16", 1800), _tk("32:15", 1840, w=60), _tk("11", 1910), _tk("23", 1300, y=420)]
    r = hb.parse_board(full, 5000)
    assert r == hb.BoardReading(5000, 16, 11, 32 * 60 + 15)
    cut = [_tk("16", 1861), _tk("32:151", 1872, w=48)]  # away score outside the frame
    r2 = hb.parse_board(cut)
    assert r2 is not None and r2.home == 16 and r2.away is None and r2.clock_s == 1935
    assert hb.parse_board([_tk("16", 10), _tk("11", 50)]) is None  # no clock, no board


def test_goals_per_side_with_gaps_and_misreads() -> None:
    br = hb.BoardReading
    reads = [
        br(0, 16, 11, 1930),
        br(2000, 16, None, 1932),
        br(4000, 16, 11, 1934),
        br(30_000, None, 12, 1960),  # board back in view, away scored meanwhile
        br(32_000, 17, 12, 1962),
        br(34_000, 17, 12, 1964),
        br(36_000, 71, 12, 1966),  # misread once
        br(38_000, 17, 12, 1968),
        br(40_000, 18, 12, 1970),
        br(42_000, 18, None, 1972),
    ]
    goals = hb.goals_from_board(reads)
    assert [(g["t_ms"], g["side"], g["score_side"], g["window_ms"]) for g in goals] == [
        (30_000, "right", 12, 26_000),  # the board was out of view since 4 s
        (32_000, "left", 17, 28_000),
        (40_000, "left", 18, 2_000),
    ]
    assert [g["score"] for g in goals] == [[16, 12], [17, 12], [18, 12]]

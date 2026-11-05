"""Hall scoreboard: parsing text tokens, goals per side from noisy, partial readings."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

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


def test_split_merged_fields() -> None:
    def texts(s: str) -> list[str]:
        return [t.text for t in hb.split_token(_tk(s, 100, w=90))]

    assert texts("16 32:10 11") == ["16", "32:10", "11"]
    assert texts("1631:2010") == ["16", "31:20", "10"]  # home, clock and away in one box
    assert texts("1631:18 10") == ["16", "31:18", "10"]
    assert texts("631:3110") == ["31:31", "10"]  # three digits before the colon: home cut off
    assert texts("32:101") == ["32:101"]  # one digit behind: maybe a cut score, the clock alone
    assert texts("18333013") == ["18", "33:30", "13"]  # the colon lost
    assert texts("18 3326 13") == ["18", "33:26", "13"]
    assert texts("1833" + chr(0xFF1A) + "3513") == ["18", "33:35", "13"]  # full-width colon
    assert texts("SGW22:25HSK") == ["SGW22:25HSK"]
    parts = hb.split_token(_tk("16 32:10 11", 100, w=110))
    assert parts[0].x2 <= parts[1].x1 + 1e-6 and parts[1].x2 <= parts[2].x1 + 1e-6


def test_parse_merged_hall_board() -> None:
    r = hb.parse_board([_tk("1631:2010", 400, w=60)], 1000)
    assert r == hb.BoardReading(1000, 16, 10, 31 * 60 + 20)


def test_parse_stacked_stream_graphic() -> None:
    clock = _tk("51:09", 605, y=90, w=70, h=26)
    # the score with team codes glued on: a score whatever the layout
    r = hb.parse_board([_tk("SGW27:30EMM", 519, y=58, w=240, h=26), clock])
    assert r is not None and (r.home, r.away, r.clock_s) == (27, 30, 51 * 60 + 9)
    # one digit after the colon is no clock either
    r = hb.parse_board([_tk("0:0", 614, y=56, w=50, h=25), _tk("00:04", 605, y=89, w=70, h=24)])
    assert r is not None and (r.home, r.away, r.clock_s) == (0, 0, 4)
    # two bare mm:ss fields: which is the score is decided over the video
    bare = [_tk("16:21", 603, y=57, w=74, h=24), _tk("44:27", 605, y=87, w=70, h=26)]
    r = hb.parse_board(bare)
    assert r is not None and r.home is None and r.away is None
    r = hb.parse_board(bare, stacked="above")
    assert r is not None and (r.home, r.away, r.clock_s) == (16, 21, 44 * 60 + 27)
    r = hb.parse_board(bare, stacked="below")
    assert r is not None and (r.home, r.away, r.clock_s) == (44, 27, 16 * 60 + 21)
    # penalty timers stacked under the clock: the score is the top line
    timers = [_tk("1:32", 700, y=88, w=50, h=24), _tk("0:08", 700, y=118, w=50, h=24)]
    r = hb.parse_board([*bare, *timers], stacked="above")
    assert r is not None and (r.home, r.away, r.clock_s) == (16, 21, 44 * 60 + 27)


def test_stacked_votes_from_codes_and_from_change() -> None:
    def frame(score: str, clock: str) -> list[hb.Token]:
        return [_tk(score, 603, y=57, w=74, h=24), _tk(clock, 605, y=87, w=70, h=26)]

    samples = [(k * 1000, frame("16:21", f"44:{20 + k:02d}")) for k in range(6)]
    assert hb.stacked_vote(samples) == "above"  # the lower field runs: it is the clock
    flipped = [(k * 1000, frame(f"44:{20 + k:02d}", "16:21")) for k in range(6)]
    assert hb.stacked_vote(flipped) == "below"
    coded = [(k * 1000, [_tk("SGW16:21", 560, y=57, w=120, h=24)]) for k in range(2)]
    coded = [(t, [*tk, _tk("44:27", 605, y=87, w=70, h=26)]) for t, tk in coded]
    assert hb.stacked_vote(coded) == "above"
    assert hb.stacked_vote(samples[:2]) is None  # too little to tell


def test_goals_decoder_ignores_outliers_and_counts_unseen_goals() -> None:
    br = hb.BoardReading
    reads = [br(k * 1000, 10, 5, None) for k in range(5)]
    reads += [br(5000, 19, 5, None)]  # a single misread
    reads += [br(6000 + k * 1000, 10, 5, None) for k in range(3)]
    # the board out of view for a minute: two home goals meanwhile
    reads += [br(70_000 + k * 1000, 12, 5, None) for k in range(3)]
    goals = hb.goals_from_board(reads)
    assert [(g["t_ms"], g["side"], g["score_side"], g["window_ms"]) for g in goals] == [
        (70_000, "left", 11, 62_000),
        (70_000, "left", 12, 62_000),
    ]
    assert [g["score"] for g in goals] == [[11, 5], [12, 5]]


def test_goals_follow_the_official_sequence() -> None:
    br = hb.BoardReading
    sequence = [[1, 0], [1, 1], [2, 1], [3, 1], [3, 2]]
    reads = [br(0, 1, 1, None), br(1000, 1, 1, None), br(2000, None, 1, None)]
    reads += [br(30_000, 3, None, None), br(31_000, 3, 1, None), br(32_000, 3, 1, None)]
    reads += [br(40_000, 8, 1, None)]  # misread
    goals = hb.goals_from_board(reads, sequence)
    assert [(g["t_ms"], g["side"], g["score"], g["window_ms"]) for g in goals] == [
        (30_000, "left", [2, 1], 29_000),
        (30_000, "left", [3, 1], 29_000),
    ]


class _FakeOcr:
    """Text detection: one box around the bright pixels; recognition: the scene's text."""

    def __init__(self) -> None:
        self.text = ""
        self.detect_calls = 0
        self.recognise_calls = 0

    def detect(self, img: NDArray[Any]) -> list[NDArray[np.float32]]:
        self.detect_calls += 1
        ys, xs = np.nonzero(img.max(axis=2) > 200)
        if len(xs) == 0:
            return []
        x1, x2, y1, y2 = xs.min(), xs.max(), ys.min(), ys.max()
        return [np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], np.float32)]

    def recognise(self, crops: list[NDArray[Any]]) -> list[tuple[str, float]]:
        self.recognise_calls += 1
        return [(self.text, 0.95) for _ in crops]


def _scene(x: int | None, y: int, w: int = 1280, h: int = 720) -> NDArray[np.uint8]:
    """A grey, textured hall with a scoreboard (light frame, dark panel, bright text) at x, y."""
    rng = np.random.default_rng(7)
    img = np.full((h, w, 3), 110, np.uint8)
    img += rng.integers(0, 40, (h, w, 1), dtype=np.uint8)
    for k in range(0, w, 37):  # wall structure
        img[:, k : k + 3] = 60
    if x is not None:
        cv2.rectangle(img, (x - 6, y - 6), (x + 166, y + 96), (185, 185, 185), -1)
        cv2.rectangle(img, (x, y), (x + 160, y + 90), (25, 25, 25), -1)
        cv2.putText(
            img, "16 32:10 11", (x + 8, y + 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (240,) * 3, 2
        )
        cv2.circle(img, (x + 40, y + 65), 12, (60, 140, 60), -1)  # a logo
    return img


def test_reader_locks_the_board_and_reads_it_cheaply() -> None:
    ocr = _FakeOcr()
    reader = hb.HallBoardReader(ocr, fps=10, every_s=1.0, full_every_s=4.0, probe_every_s=0.5)
    ocr.text = "16 32:10 11"
    still = _scene(500, 200)
    for k in range(5):  # a fixed camera: recognition alone after the first read
        reader.add(k * 10, still)
    assert ocr.detect_calls == 1 and reader.stats.boxes == 4
    ocr.text = "17 32:15 11"  # a new score: read in full to make sure
    reader.add(50, still)
    assert ocr.detect_calls == 2
    for k in range(6, 9):  # the camera pans: the board is found elsewhere
        reader.add(k * 10, _scene(500 - 60 * (k - 5), 200 + 10 * (k - 5)))
    assert reader.stats.found == 8
    blank = _scene(None, 0)  # out of view: probes every 0.5 s, the whole frame every 4 s
    for i in range(90, 150):
        reader.add(i, blank)
    assert reader.stats.full == 1 + 2 and reader.stats.probes == 8 + 12
    reads = reader.readings
    assert len(reads) == 9 and {(r.home, r.away) for r in reads} == {(16, 11), (17, 11)}
    s = reader.summary()
    assert [(g["t_ms"], g["side"], g["score_side"]) for g in s["goals"]] == [(5000, "left", 17)]


def test_clock_of_a_stream_graphic_with_penalty_timers() -> None:
    clock = _tk("42:26", 593, y=90, w=95, h=28)
    timer = _tk("0:18", 690, y=90, w=80, h=28)  # beside the clock, same size
    # a score with codes over clock and timer: the field most centred under it is the clock
    wide = _tk("SGW 19 : 16 GOS", 505, y=58, w=270, h=28)
    r = hb.parse_board([wide, timer, clock])
    assert r is not None and (r.home, r.away, r.clock_s) == (19, 16, 42 * 60 + 26)
    # no score read: of two fields of the same size, the one with two-digit minutes
    r = hb.parse_board([timer, clock])
    assert r is not None and r.clock_s == 42 * 60 + 26
    # bare score over the clock, a timer on the line under the clock: the line next to the score
    score = _tk("19:16", 593, y=58, w=95, h=28)
    under = _tk("1:32", 600, y=122, w=80, h=28)
    r = hb.parse_board([score, under, clock], stacked="above")
    assert r is not None and (r.home, r.away, r.clock_s) == (19, 16, 42 * 60 + 26)
    # the layout not known yet: either field may be the clock, so no clock at all
    r = hb.parse_board([score, clock])
    assert r is not None and r.clock_s is None
    # a pre-match graphic ("16:00 Uhr") is no clock
    assert hb.parse_board([_tk("16:00 Uhr", 535, y=562, w=210, h=39)]) is None

"""Halves, labels and the clocks.json merge of ml/data/segment_clock.py (synthetic readings), and
the clock read of a real clip when it is available locally."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from segment_clock import (
    REPO,
    game_labels,
    labels,
    merge_clocks,
    read_segment_clock,
    segment_halves,
)


def running(c0_s: int, c1_s: int, every_s: int = 5, v0_ms: int = 0) -> list[list[float]]:
    return [[v0_ms + (c - c0_s) * 1000, float(c)] for c in range(c0_s, c1_s + 1, every_s)]


def seg(k: int, start_s: float, samples: list[list[float]], source: str = "overlay") -> dict[str, Any]:
    return {
        "file": f"g_s{k}.mp4",
        "start_s": start_s,
        "clock": {"source": source if samples else None, "samples": samples},
    }


def log_entry(t: int, action: str = "Tor", result: str = "1:0") -> dict[str, Any]:
    return {
        "actionGroup": 1, "actionText": action, "homeTeamPlayerStaffName": "A B",
        "homeTeamPlayerStaffNrDesc": "7", "awayTeamPlayerStaffName": "",
        "awayTeamPlayerStaffNrDesc": "", "result": result, "timeInt": t,
        "timeString": f"{t // 60:02d}:{t % 60:02d}",
    }


def test_restarting_second_half_is_found_from_the_drop_between_segments() -> None:
    segs = [
        seg(0, 900, running(600, 780)),  # first half 10:00-13:00
        seg(1, 4000, running(300, 480)),  # clock restarted: 05:00 is 35:00
        seg(2, 5000, []),
    ]
    assert segment_halves(segs) == [(1, True), (2, True), (1, False)]


def test_first_half_clock_without_a_second_half_in_view_is_uncertain() -> None:
    assert segment_halves([seg(0, 900, running(600, 780))]) == [(1, False)]
    # a continuing second half (30-60) is certain on its own
    assert segment_halves([seg(0, 4000, running(2100, 2280))]) == [(2, True)]


def test_labels_place_entries_with_segment_ms_and_video_offset() -> None:
    game = {
        "duration_s": 6000.0,
        "segments": [seg(0, 900, running(600, 780, v0_ms=2000)), seg(1, 4000, running(300, 480))],
    }
    official = {
        "log": [log_entry(650), log_entry(2000, "Wurf Parade", "1:0"), log_entry(2100, result="2:0"),
                log_entry(30 * 60 + 400, result="3:0")]
    }
    out = game_labels("g", game, official)
    placed = [(e["segment"], e["segment_ms"], e["video_ms"], e["kind"]) for e in out["entries"]]
    assert placed == [
        ("g_s0.mp4", 52_000, 952_000, "goal"),  # 50 s after 10:00, which shows at 2 s
        ("g_s1.mp4", 0, 4_000_000, "goal"),  # 35:00 shows as 05:00 (restarted clock)
        ("g_s1.mp4", 100_000, 4_100_000, "goal"),  # 36:40 = 06:40
    ]  # the save at 33:20 is 100 s before the first reading: not placed
    assert out["entries"][0]["anchor_gap_s"] == 0
    assert out["counts"] == {"goal": 3}
    assert [s["entries"] for s in out["segments"]] == [1, 2]


def test_merge_fills_only_segments_without_clock() -> None:
    state: dict[str, Any] = {"games": {"g": {"segments": [
        {"file": "a.mp4"}, {"file": "b.mp4", "clock": {"source": None, "samples": []}}
    ]}}}
    side = {"g": {"a.mp4": {"source": "overlay", "samples": [[0, 1.0], [5000, 6.0]]},
                  "b.mp4": {"source": "overlay", "samples": [[0, 1.0]]}}, "other": {}}
    assert merge_clocks(state, side) == 1
    g = state["games"]["g"]
    assert g["segments"][0]["clock"]["source"] == "overlay"
    assert g["segments"][1]["clock"]["source"] is None
    assert g["has_clock"] is True


def test_labels_writes_games_with_log_and_clock(tmp_path: Path) -> None:
    work, off, out = tmp_path / "w", tmp_path / "off", tmp_path / "out"
    work.mkdir()
    off.mkdir()
    state = {"batch": 2, "games": {
        "with": {"duration_s": 3000.0, "segments": [seg(0, 900, running(600, 780))]},
        "nolog": {"duration_s": 3000.0, "segments": [seg(0, 900, running(600, 780))]},
        "noclock": {"duration_s": 3000.0, "segments": [{"file": "x.mp4", "start_s": 0}]},
    }}
    (work / "state.json").write_text(json.dumps(state))
    for n, log in (("with", [log_entry(700)]), ("nolog", []), ("noclock", [log_entry(700)])):
        (off / f"{n}.json").write_text(json.dumps({"log": log}))
    written = labels(work, out, off)
    assert [p.name for p in written] == ["with.json"]
    assert json.loads(written[0].read_text())["entries"][0]["segment_ms"] == 100_000


CLIP = REPO / "data" / "videos" / "ch-spl2-2024-leimental-arbon.mp4"


@pytest.mark.skipif(
    not CLIP.exists() or shutil.which("tesseract") is None, reason="test clip or tesseract missing"
)
def test_overlay_clock_of_the_leimental_clip() -> None:
    r = read_segment_clock(CLIP)
    assert r["source"] == "overlay"
    s = r["samples"]
    assert len(s) >= 40  # 5 minutes, a reading every 5 s
    assert all(b[0] - a[0] >= 4500 for a, b in zip(s, s[1:], strict=False))  # once per 5 s
    # the clip shows the match clock from about 02:00 to 07:00
    assert 100 <= s[0][1] <= 150 and 400 <= s[-1][1] <= 440


def test_plausible_needs_a_running_or_a_standing_clock() -> None:
    from segment_clock import plausible

    run = [(v, c) for v, c in running(600, 700)]
    assert plausible(run)
    assert plausible([(0, 190.0), (5000, 190.0), (10000, 190.0)])  # time-out: stands still
    slow = [(k * 5000, 190.0 + k // 6) for k in range(36)]  # one "second" per 30 s
    assert not plausible(slow)
    assert not plausible([(0, 100.0)])


def test_clean_drops_a_misread_twice_in_a_row_but_keeps_a_half_restart() -> None:
    from segment_clock import clean

    a = [(k * 2000, 2267.0 + k * 2) for k in range(10)]  # running 37:47 ...
    bad = [(20_000, 2390.0), (22_000, 2392.0)]  # "39:50", "39:52" read for 37:xx
    b = [(24_000 + k * 2000, 2291.0 + k * 2) for k in range(10)]
    assert clean([*a, *bad, *b]) == [*a, *b]
    restart = [(0, 1795.0), (2000, 1797.0), (60_000, 0.0), (62_000, 2.0)]  # 2nd half from 0
    assert clean(restart) == restart

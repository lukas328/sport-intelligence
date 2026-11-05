"""match_to_video on synthetic clock readings (ml/eval/align_official.py)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from align_official import (
    match_to_video,
    official_entries,
    samples_from_overlay,
)


def running(v0_ms: int, c0_s: int, c1_s: int, every_s: int = 5) -> list[tuple[int, float]]:
    """Readings of a clock that runs from c0 to c1, starting at video time v0."""
    return [(v0_ms + (c - c0_s) * 1000, float(c)) for c in range(c0_s, c1_s + 1, every_s)]


def test_running_clock_interpolates_at_one_second_per_second() -> None:
    s = running(10_000, 120, 420)  # clock 02:00 at video 0:10
    assert match_to_video(s, 120) == 10_000
    assert match_to_video(s, 179) == 69_000  # between two readings
    assert match_to_video(s, 420) == 310_000


def test_readings_need_not_be_sorted_and_isolated_misreads_are_dropped() -> None:
    s = running(0, 600, 900)
    s.reverse()
    s.insert(10, (150_000, 1700.0))  # 28:20 misread in the middle
    assert match_to_video(s, 750) == 150_000


def test_reading_jitter_is_averaged_along_a_run() -> None:
    # every third reading is taken just before the clock ticks over and reads a second low
    s = [(v, c - 1 if k % 3 == 2 else c) for k, (v, c) in enumerate(running(0, 600, 900))]
    assert match_to_video(s, 610) == 10_000
    assert match_to_video(s, 611) == 11_000  # the low reading (609 at 10 s) is moved to 9 s


def test_time_out_pause() -> None:
    # clock runs 10:00 -> 12:00, stands at 12:00 for 60 s (time-out), runs on to 14:00
    s = running(0, 600, 720) + [(t, 720.0) for t in range(125_000, 180_001, 5_000)]
    s += running(180_000, 720, 840)
    assert match_to_video(s, 700) == 100_000  # before the stop
    assert match_to_video(s, 720) == 120_000  # the time-out itself: when the clock stopped
    assert match_to_video(s, 725) == 185_000  # after: counted from the restart
    assert match_to_video(s, 840) == 300_000


def test_stop_between_readings_stays_inside_the_bracket() -> None:
    # sparse readings around an unseen 40 s stop: 10:00 at 0 s, 11:00 at 100 s
    s = [(0, 600.0), (100_000, 660.0)]
    assert match_to_video(s, 610) == 10_000  # nearer the reading below: count on
    assert match_to_video(s, 650) == 90_000  # nearer the reading above: count back


def test_second_half_restarting_at_zero() -> None:
    first = running(0, 1500, 1800)  # 25:00 .. 30:00
    second = running(900_000, 0, 300)  # after the break the clock restarts at 00:00
    s = first + second
    assert match_to_video(s, 1790) == 290_000
    assert match_to_video(s, 1800) == 300_000  # 30:00 ends the first half
    assert match_to_video(s, 1801) == 901_000  # 30:01 is 00:01 of the second half
    assert match_to_video(s, 2000) == 1_100_000


def test_second_half_continuing_at_thirty() -> None:
    s = running(0, 1500, 1800) + running(900_000, 1800, 2100)
    assert match_to_video(s, 1795) == 295_000
    assert match_to_video(s, 1805) == 905_000  # not counted on from the end of the first half
    assert match_to_video(s, 2100) == 1_200_000


def test_clip_of_a_restarting_second_half_needs_the_half() -> None:
    s = running(0, 300, 600)  # 05:00 .. 10:00, no half boundary in view
    assert match_to_video(s, 400) == 100_000  # read as the first half by default
    assert match_to_video(s, 1800 + 400, start_half=2) == 100_000
    assert match_to_video(s, 1800 + 400) is None


def test_out_of_range() -> None:
    s = running(30_000, 120, 420)  # 02:00 .. 07:00
    assert match_to_video(s, 90) == 0  # 30 s before the first reading: extrapolated
    assert match_to_video(s, 470) == 380_000  # 50 s after the last
    assert match_to_video(s, 59) is None  # more than 60 s before
    assert match_to_video(s, 481) is None  # more than 60 s after
    assert match_to_video(s, 2000) is None  # other half
    assert match_to_video([], 100) is None


def test_overlay_segments_and_log_shapes() -> None:
    segs = [{"start_ms": 0, "start_clock_s": 120, "end_ms": 60_000, "reads": 5}]
    assert samples_from_overlay(segs, 30_000) == [(0, 120.0), (30_000, 150.0), (60_000, 180.0)]
    ch = {
        "log": [
            {
                "actionGroup": 2,
                "actionText": "Wurf Parade",
                "homeTeamPlayerStaffName": "KEEPER A",
                "homeTeamPlayerStaffNrDesc": "1",
                "awayTeamPlayerStaffName": "SHOOTER B",
                "awayTeamPlayerStaffNrDesc": "6",
                "result": "0:0",
                "timeInt": 42,
                "timeString": "00:42",
            }
        ],
        "players": [{"isHome": 1, "dressNr": 1, "function": "goalkeeper"}],
    }
    (row,) = official_entries(ch)
    assert (row["kind"], row["team"], row["number"]) == ("shot_saved", "away", 6)
    assert row["goalkeeper"] == {"number": 1, "name": "KEEPER A"}
    dhb = {
        "log": [
            {
                "timeInt": 53,
                "actionText": "Tor",
                "team": "home",
                "number": 7,
                "name": "X",
                "result": "1:0",
            }
        ]
    }
    (row,) = official_entries(dhb)
    assert (row["kind"], row["score"], row["match_s"]) == ("goal", [1, 0], 53)

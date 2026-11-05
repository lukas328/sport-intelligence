"""Shirt numbers: voting per track, splitting at identity switches, joining fragments."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest

from handball_vision.numbers import NumberReader, Reading, split_points, stretch_contrast, vote
from handball_vision.pipeline import merge_by_number, split_by_reading_colour
from handball_vision.teams import TeamAssigner, colour_runs, side_of, team_centres
from handball_vision.tracking import TrackPoint

MODELS = Path(__file__).resolve().parents[3] / "data" / "models"


def r(n: int, c: float, f: int = -1) -> Reading:
    return Reading(n, c, f)


def test_vote_needs_agreement_and_enough_readings() -> None:
    assert vote([r(14, 0.9), r(14, 0.95), r(14, 0.85)]) is not None
    v = vote([r(14, 0.9), r(14, 0.95), r(14, 0.85), r(4, 0.9)])
    assert v is not None and v.number == 14 and v.readings == 3
    assert vote([r(2, 0.85), r(2, 0.9)]) is None  # two ordinary readings: not enough
    assert vote([r(5, 0.97), r(5, 0.99)]) is not None  # two very sure ones and nothing else
    assert vote([r(14, 0.9), r(14, 0.9), r(14, 0.9), r(43, 0.9), r(43, 0.9)]) is None  # 60 %
    assert vote([r(14, 0.5)] * 10) is None  # unsure readings never count


def test_roster_maps_known_misreadings() -> None:
    roster = {11, 7, 33}
    # 11 read as 44 (1 <-> 4 in both places) and as 1 (a dropped digit)
    v = vote([r(44, 0.9), r(44, 0.92), r(11, 0.9), r(1, 0.85)], allowed=roster)
    assert v is not None and v.number == 11 and v.readings == 4 and v.corrected == 3
    v = vote([r(1, 0.9), r(1, 0.9), r(7, 0.9), r(7, 0.9)], allowed={7})  # 1 <-> 7
    assert v is not None and v.number == 7 and v.readings == 4 and v.corrected == 2
    v = vote([r(8, 0.9)] * 3, allowed={3, 5})  # 3 <-> 8
    assert v is not None and v.number == 3
    v = vote([r(44, 0.9)] * 3, allowed={4, 9})  # a doubled digit
    assert v is not None and v.number == 4
    v = vote([r(133, 0.9)] * 3, allowed={13})  # a doubled digit in 3-digit garbage
    assert v is not None and v.number == 13


def test_roster_ignores_garbage_and_ambiguous_misreadings() -> None:
    roster = {11, 4, 33}
    # 58, 27 and 583 are no known misreading of a roster number: ignored, so 33 keeps its 100 %
    v = vote([r(33, 0.9)] * 3 + [r(58, 0.95), r(27, 0.9), r(583, 0.9)], allowed=roster)
    assert v is not None and v.number == 33 and v.readings == 3 and v.corrected == 0
    assert vote([r(58, 0.95)] * 5, allowed=roster) is None
    # 44 fits both 4 and 11: without a direct reading of either it counts for neither
    assert vote([r(44, 0.9)] * 4, allowed=roster) is None
    v = vote([r(44, 0.9)] * 3 + [r(4, 0.9)], allowed=roster)
    assert v is not None and v.number == 4 and v.corrected == 3
    # the result is on the roster or None, even when everyone agrees on another number
    assert vote([r(14, 0.95)] * 6, allowed={40, 41}) is None
    assert vote([r(14, 0.9)] * 3, allowed=set()) is None
    assert vote([r(44, 0.5)] * 5, allowed={11}) is None  # unsure readings still never count
    # two very sure readings are not enough when something else was read, even if ignored
    assert vote([r(33, 0.97), r(33, 0.98), r(56, 0.9)], allowed={33, 7}) is None
    assert vote([r(33, 0.97), r(33, 0.98)], allowed={33, 7}) is not None


def test_without_roster_the_vote_is_unchanged() -> None:
    reads = [r(44, 0.9), r(44, 0.92), r(44, 0.9), r(11, 0.9)]
    v = vote(reads)
    assert v is not None and v.number == 44 and v.corrected == 0
    assert vote(reads, allowed=None) == v
    v = vote(reads, allowed={11})
    assert v is not None and v.number == 11 and v.readings == 4


def test_merge_uses_the_team_roster() -> None:
    pts = _points(1, range(0, 100)) + _points(2, range(150, 300)) + _points(3, range(0, 300), 30)
    team = {
        1: {"label": "home", "confidence": 0.9, "samples": 10},
        2: {"label": "home_gk", "confidence": 0.9, "samples": 10},
        3: {"label": "away", "confidence": 0.9, "samples": 10},
    }
    reads = {
        1: [r(11, 0.95, f) for f in (10, 40, 70)],
        2: [r(44, 0.9, f) for f in (160, 200, 250)],
        3: [r(44, 0.9, f) for f in (10, 100, 200)],
    }
    out, merged = merge_by_number(pts, team, reads, fps=30.0, rosters={"home": {11, 12}})
    assert merged == 1 and {p.track_id for p in out} == {1, 3}
    assert team[1]["number"] == 11 and team[3]["number"] == 44  # the away team has no roster


def test_split_where_the_numbers_change() -> None:
    reads = [r(43, 0.9, f) for f in (10, 40, 70, 100)] + [r(5, 0.95, f) for f in (200, 230, 260)]
    assert split_points(reads) == [150]
    # one stray reading inside is not a switch
    assert split_points([r(43, 0.9, f) for f in range(0, 300, 30)] + [r(33, 0.9, 155)]) == []


def _points(track: int, frames: range, x: float = 10.0) -> list[TrackPoint]:
    return [TrackPoint(track, f, x, 5.0, 0.0, 0.0, True, 0) for f in frames]


def test_fragments_with_the_same_number_become_one_player() -> None:
    pts = _points(1, range(0, 100)) + _points(2, range(150, 300)) + _points(3, range(0, 300), 30)
    team = {t: {"label": "home", "confidence": 0.9, "samples": 10} for t in (1, 2, 3)}
    reads = {
        1: [r(7, 0.95, f) for f in (10, 40, 70)],
        2: [r(7, 0.9, f) for f in (160, 200, 250)],
        3: [r(9, 0.9, f) for f in (10, 100, 200)],
    }
    out, merged = merge_by_number(pts, team, reads, fps=30.0)
    assert merged == 1
    tracks = {p.track_id for p in out}
    assert tracks == {1, 3}
    assert team[1]["number"] == 7 and team[1]["merged_from"] == [2] and team[3]["number"] == 9
    # the readings follow the joined track (re-identification uses them per final track)
    assert sorted(x.frame for x in reads[1]) == [10, 40, 70, 160, 200, 250] and 2 not in reads


def test_a_swapped_track_is_cut_and_both_parts_get_their_number() -> None:
    pts = _points(1, range(0, 300))
    team = {1: {"label": "away", "confidence": 0.9, "samples": 10}}
    reads = {
        1: [r(43, 0.9, f) for f in (10, 40, 70, 100)] + [r(5, 0.95, f) for f in (200, 230, 260)]
    }
    out, _ = merge_by_number(pts, team, reads, fps=30.0)
    by: dict[int, list[int]] = {}
    for p in out:
        by.setdefault(p.track_id, []).append(p.frame)
    assert len(by) == 2
    numbers = sorted((min(fr), team[t]["number"]) for t, fr in by.items())
    assert numbers == [(0, 43), (150, 5)]
    # and so do the readings of the cut-off part
    assert {t: {x.number for x in rs} for t, rs in reads.items()} == {1: {43}, 2: {5}}


def test_role_samples_follow_cuts_and_joins() -> None:
    pts = _points(1, range(0, 300)) + _points(3, range(400, 500))
    team = {t: {"label": "away", "confidence": 0.9, "samples": 10} for t in (1, 3)}
    reads = {
        1: [r(43, 0.9, f) for f in (10, 40, 70, 100)] + [r(5, 0.95, f) for f in (200, 230, 260)],
        3: [r(5, 0.95, f) for f in (410, 440, 470)],
    }
    p = np.array([0.9, 0.05, 0.05])
    roles: dict[int, list[tuple[int, Any]]] = {1: [(30, p), (240, p)], 3: [(450, p)]}
    out, merged = merge_by_number(pts, team, reads, fps=30.0, roles=roles)
    later = next(t for t in {q.track_id for q in out} if t != 1)
    assert merged == 1  # the cut-off #5 and track 3 are one player
    assert {t: [f for f, _ in v] for t, v in roles.items()} == {1: [30], later: [240, 450]}


def test_overlapping_fragments_keep_only_the_stronger_number() -> None:
    pts = _points(1, range(0, 300)) + _points(2, range(100, 200), 20)
    team = {t: {"label": "home", "confidence": 0.9, "samples": 10} for t in (1, 2)}
    reads = {
        1: [r(7, 0.95, f) for f in range(0, 300, 30)],
        2: [r(7, 0.9, f) for f in (110, 150, 190)],
    }
    _, merged = merge_by_number(pts, team, reads, fps=30.0)
    assert merged == 0 and team[1]["number"] == 7 and "number" not in team[2]


WHITE, BLACK = [200.0, 128.0, 128.0], [35.0, 128.0, 128.0]


def _colours(
    team: TeamAssigner, track: int, frames: range, colour: list[float], noise: float = 0.0
) -> None:
    rng = np.random.default_rng(track)
    for f in frames:
        team.add_sample(track, np.asarray(colour) + rng.normal(0, noise, 3), f)


def test_single_looks_get_the_team_of_their_colour() -> None:
    team_out = {
        1: {"label": "home", "lab": WHITE},
        2: {"label": "home", "lab": [150.0, 128.0, 128.0]},  # a mixed track pulls the median
        3: {"label": "away", "lab": BLACK},
        4: {"label": "away", "lab": [60.0, 128.0, 128.0]},
    }
    samples = {
        1: [np.array(WHITE)] * 30,
        2: [np.array(WHITE)] * 10 + [np.array(BLACK)] * 10,
        3: [np.array(BLACK)] * 30,
        4: [np.array(BLACK)] * 10,
    }
    centres = team_centres(team_out, samples)
    # the looks, not the track medians: white and black as they are seen
    assert abs(centres["home"][0] - 200) < 1 and abs(centres["away"][0] - 35) < 1
    assert side_of(np.array([190.0, 128, 128]), centres) == "home"
    assert side_of(np.array([40.0, 128, 128]), centres) == "away"
    assert side_of(np.array([118.0, 128, 128]), centres) is None  # halfway: unsure
    assert side_of(None, centres) is None
    # teams too alike, or too few tracks: no single-look teams
    grey = {t: {**v, "lab": [100.0, 128.0, 128.0]} for t, v in team_out.items()}
    assert team_centres(grey, {}) == {}
    assert team_centres({1: team_out[1], 3: team_out[3]}, samples) == {}


def test_colour_runs_ignore_flicker() -> None:
    frames = list(range(0, 300, 3))
    sides: list[str | None] = ["home" if f < 150 else "away" for f in frames]
    sides[10] = "away"  # one look in a crowd
    sides[20] = None
    sides[70:74] = ["home"] * 4  # 0.5 s: too short to be another person
    assert colour_runs(frames, sides, fps=25.0) == [(0, 147, "home"), (150, 297, "away")]
    assert colour_runs(frames, [None] * len(frames), fps=25.0) == []


def test_a_number_read_on_the_other_teams_shirt_is_cut_out() -> None:
    kits = {"home": (240, 240, 240), "away": (30, 30, 30)}
    team = TeamAssigner(kits)
    _colours(team, 1, range(0, 150, 3), WHITE, 3.0)  # a white player, then a black one
    _colours(team, 1, range(150, 300, 3), BLACK, 3.0)
    _colours(team, 2, range(0, 300, 3), WHITE)
    _colours(team, 3, range(0, 300, 3), BLACK)
    _colours(team, 4, range(0, 300, 3), BLACK)
    _colours(team, 5, range(0, 300, 3), WHITE)  # a white player with a stray black reading
    _colours(team, 6, range(0, 300, 3), BLACK)  # a goalkeeper: never cut
    team_out: dict[int, dict[str, Any]] = {
        t: {"label": lab, "lab": WHITE if lab == "home" else BLACK, "confidence": 0.9}
        for t, lab in ((1, "home"), (2, "home"), (3, "away"), (4, "away"), (5, "home"))
    }
    team_out[6] = {"label": "home_gk", "lab": BLACK, "confidence": 0.9}
    team.samples[5][50] = np.asarray(BLACK)
    pts = [p for t in range(1, 7) for p in _points(t, range(0, 300, 3))]
    reads = {
        1: [r(7, 0.95, f) for f in (30, 60, 90)] + [r(8, 0.9, f) for f in (180, 210, 240)],
        5: [r(4, 0.95, f) for f in (30, 60, 90)] + [r(8, 0.95, 150)],
        6: [r(1, 0.95, f) for f in (30, 60, 90)],
    }
    looks: dict[int, list[tuple[int, Any]]] = {1: [(30, "a"), (240, "b")]}
    out, stats = split_by_reading_colour(pts, team_out, team, reads, [looks], fps=25.0)
    assert stats == {"tracks_split": 1, "pieces": 2, "readings_dropped": 1}
    new = max(team_out)
    assert team_out[1]["label"] == "home"
    assert team_out[new]["label"] == "away" and team_out[new]["label_source"] == "reading_colour"
    assert team_out[new]["lab"][0] < 50 and team_out[1]["lab"][0] > 150
    frames = {t: sorted(p.frame for p in out if p.track_id == t) for t in (1, new)}
    assert frames[1][-1] < 150 <= frames[new][0]
    assert {x.number for x in reads[1]} == {7} and {x.number for x in reads[new]} == {8}
    assert looks == {1: [(30, "a")], new: [(240, "b")]}
    assert [x.number for x in reads[5]] == [4, 4, 4]  # the stray reading is dropped
    assert len(reads[6]) == 3 and team_out[6]["label"] == "home_gk"
    # the number vote afterwards: two players, one per team
    merge_by_number(out, team_out, reads, fps=25.0)
    assert (team_out[1]["number"], team_out[new]["number"]) == (7, 8)


@pytest.mark.skipif(
    not (MODELS / "ch_PP-OCRv4_rec_infer.onnx").exists(), reason="text models not downloaded"
)
def test_reads_a_printed_shirt_number() -> None:
    reader = NumberReader(
        MODELS / "ch_PP-OCRv4_det_infer.onnx", MODELS / "ch_PP-OCRv4_rec_infer.onnx", threads=1
    )
    img = np.full((160, 70, 3), (40, 180, 230), np.uint8)  # yellow shirt (BGR)
    cv2.putText(img, "14", (10, 75), cv2.FONT_HERSHEY_DUPLEX, 1.1, (20, 20, 20), 3)
    got = reader.read_player(img, (0, 0, 70, 160))
    assert got is not None and got.number == 14 and got.confidence > 0.8


def test_stretch_spreads_a_faint_channel() -> None:
    faint = np.full((40, 30), 180, np.uint8)
    faint[10:30, 10:20] = 160  # a mid-grey digit on a light-grey shirt
    out = stretch_contrast(faint)
    assert out.min() == 0 and out.max() == 255
    assert out[20, 15] < 10 and out[0, 0] > 245
    flat = np.full((8, 8), 77, np.uint8)
    assert np.array_equal(stretch_contrast(flat), flat)  # nothing to stretch: unchanged


@pytest.mark.skipif(
    not (MODELS / "ch_PP-OCRv4_rec_infer.onnx").exists(), reason="text models not downloaded"
)
def test_reads_a_faint_number_on_a_white_shirt() -> None:
    """White shirt in a dim hall: light grey with a slightly darker, blurred number (stream
    footage). The text detector finds it only after the contrast stretch."""
    reader = NumberReader(
        MODELS / "ch_PP-OCRv4_det_infer.onnx", MODELS / "ch_PP-OCRv4_rec_infer.onnx", threads=1
    )
    img = np.full((100, 44, 3), (178, 182, 186), np.uint8)
    cv2.putText(img, "9", (12, 42), cv2.FONT_HERSHEY_DUPLEX, 0.8, (155, 165, 170), 2)
    blurred = cv2.GaussianBlur(img, (3, 3), 0)
    got = reader.read_player(blurred, (0, 0, 44, 100))
    assert got is not None and got.number == 9 and got.confidence > 0.8

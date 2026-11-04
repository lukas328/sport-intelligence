"""Shirt numbers: voting per track, splitting at identity switches, joining fragments."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from handball_vision.numbers import NumberReader, Reading, split_points, vote
from handball_vision.pipeline import merge_by_number
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


def test_overlapping_fragments_keep_only_the_stronger_number() -> None:
    pts = _points(1, range(0, 300)) + _points(2, range(100, 200), 20)
    team = {t: {"label": "home", "confidence": 0.9, "samples": 10} for t in (1, 2)}
    reads = {
        1: [r(7, 0.95, f) for f in range(0, 300, 30)],
        2: [r(7, 0.9, f) for f in (110, 150, 190)],
    }
    _, merged = merge_by_number(pts, team, reads, fps=30.0)
    assert merged == 0 and team[1]["number"] == 7 and "number" not in team[2]


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

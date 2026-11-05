"""Score overlay: finding it, reading it, cleaning noisy readings."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from handball_vision import scoreboard as sb

FPS = 10.0
W, H = 960, 540


WHITE = (255, 255, 255)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def _frame(
    score: tuple[int, int], clock_s: int, rng: np.random.Generator, banner: str | None = None
) -> np.ndarray:
    """A panning 'hall' (texture shifted every frame) with a score bug at the top."""
    base = rng.integers(40, 200, size=(H // 8, W // 8, 3), dtype=np.uint8)
    img = cv2.resize(base, (W, H), interpolation=cv2.INTER_LINEAR)
    # score box (white on red) and clock box (dark on light grey)
    cv2.rectangle(img, (360, 20), (660, 70), (40, 30, 200), -1)
    cv2.putText(img, "HOM", (372, 58), FONT, 1.0, WHITE, 2)
    cv2.putText(img, f"{score[0]} : {score[1]}", (470, 58), FONT, 1.0, WHITE, 2)
    cv2.putText(img, "AWY", (580, 58), FONT, 1.0, WHITE, 2)
    cv2.rectangle(img, (455, 74), (565, 110), (225, 225, 225), -1)
    text = f"{clock_s // 60:02d}:{clock_s % 60:02d}"
    cv2.putText(img, text, (462, 102), FONT, 0.9, (40, 40, 40), 2)
    if banner:  # name banner in the overlay red, right side = away team
        cv2.rectangle(img, (720, 30), (950, 62), (40, 30, 200), -1)
        cv2.putText(img, banner, (728, 55), FONT, 0.7, WHITE, 2)
    return img


def _video(seconds: int = 40) -> list[np.ndarray]:
    rng = np.random.default_rng(3)
    out = []
    for k in range(int(seconds * FPS)):
        t = k / FPS
        score = (1, 0) if t < 12 else (2, 0) if t < 25 else (2, 1)
        banner = "11 Sophie DUMMLER" if 26 <= t < 30 else None
        out.append(_frame(score, 120 + int(t), rng, banner))
    return out


def test_goals_from_noisy_readings() -> None:
    reads = [
        (0, (1, 0)),
        (1000, (1, 0)),
        (2000, (41, 0)),  # misreading, once
        (3000, (1, 0)),
        (4000, (1, 1)),
        (5000, (1, 1)),
        (6000, (2, 7)),  # misreading twice in a row: a jump by six, ignored
        (7000, (2, 7)),
        (8000, (2, 1)),
        (9000, (2, 1)),
        (10_000, (2, 1)),
    ]
    goals = sb.goals_from_scores(reads)
    assert [(g.t_ms, g.side, g.score) for g in goals] == [
        (4000, "right", (1, 1)),
        (8000, "left", (2, 1)),
    ]
    assert sb.first_score(reads) == (1, 0)


def test_two_goals_while_the_overlay_was_hidden() -> None:
    reads = [(k * 1000, (3, 3)) for k in range(4)] + [(10_000 + k * 1000, (4, 4)) for k in range(6)]
    goals = sb.goals_from_scores(reads)
    assert [(g.side, g.score) for g in goals] == [("left", (4, 4)), ("right", (4, 4))]


def test_clock_runs_and_stops() -> None:
    reads = [(t * 1000, 120 + t) for t in range(0, 60, 5)]  # runs
    reads += [(t * 1000, 175) for t in range(65, 120, 5)]  # timeout: stands at 2:55
    reads += [(t * 1000, 175 + (t - 120)) for t in range(120, 180, 5)]  # runs again
    segs = sb.clock_segments(reads)
    assert [(s["start_ms"], s["start_clock_s"]) for s in segs] == [(0, 120), (120_000, 175)]
    assert segs[0]["end_ms"] == 55_000


def test_banner_texts_and_votes() -> None:
    assert sb.parse_banner("| 7 Amy MUSTERMANN |") == (7, "Amy MUSTERMANN")
    assert sb.parse_banner("33DeniseSAMPLER") == (33, "Denise SAMPLER")
    assert sb.parse_banner("11. Sophie DUMMLER |") == (11, "Sophie DUMMLER")
    assert sb.parse_banner("ARB") is None
    reads = [
        (174_000, "right", "11 Sophie DUMMLER"),
        (175_000, "right", "e . 11 Sophie DUMMLER |"),
        (291_000, "right", "} 44. Sophie DUMMLER |"),  # misread number, same name
        (292_000, "right", "} 44 Sophie DUMMLER |"),
        (92_000, "left", "| 7 Lisa ZUFALL ton"),
    ]
    shown = sb.banners(sorted(reads))
    assert [(b["t_ms"], b["side"], b["number"]) for b in shown] == [
        (92_000, "left", 7),
        (174_000, "right", 11),
        (291_000, "right", 11),  # the name keeps its number
    ]
    goals = [sb.Goal(91_000, "left", (2, 1)), sb.Goal(173_000, "right", (2, 3))]
    attached = sb.attach_scorers(goals, shown)
    assert [g["scorer"]["name"] for g in attached] == ["Lisa ZUFALL", "Sophie DUMMLER"]


def test_parsers() -> None:
    assert sb.parse_score("12:10") == (12, 10)
    assert sb.parse_score("2 - 1") == (2, 1)
    assert sb.parse_score("2:") is None
    assert sb.parse_clock("03:34") == 214
    assert sb.parse_clock("3:74") is None


def test_no_overlay_in_a_plain_or_fixed_video() -> None:
    rng = np.random.default_rng(1)
    moving = [rng.integers(0, 255, size=(H, W, 3), dtype=np.uint8) for _ in range(12)]
    assert sb.find_overlay(moving) == []
    still = [np.full((H, W, 3), 120, np.uint8)] * 12
    assert sb.find_overlay(still) == []


@pytest.mark.skipif(not sb.available(), reason="tesseract not installed")
def test_reads_score_and_clock_from_a_video() -> None:
    frames = _video()
    sample = frames[:: len(frames) // 24][:24]
    boxes = sb.find_overlay(sample)
    assert boxes, "overlay not found"
    x, y, w, h = sb._union(boxes, 6, (W, H))
    assert y < 40 and x < 380 and x + w > 640
    step = len(frames) // 24
    crops = [(k * step / FPS, f[y : y + h, x : x + w]) for k, f in enumerate(sample)][::3]
    fields = sb.find_fields(crops, (x, y))
    assert {f.kind for f in fields} == {"score", "clock"}
    reader = sb.Reader(fields, FPS, clock_every_s=5)
    for i, f in enumerate(frames):
        reader.add(i, f)
    summary = sb.read_overlay_summary(reader)
    assert summary["first_score"] == (1, 0)
    assert [(g["side"], g["score"]) for g in summary["goals"]] == [
        ("left", [2, 0]),
        ("right", [2, 1]),
    ]
    assert abs(summary["goals"][0]["t_ms"] - 12_000) <= 1000
    assert abs(summary["goals"][1]["t_ms"] - 25_000) <= 1000
    assert summary["goals"][1]["scorer"] == {"number": 11, "name": "Sophie DUMMLER"}
    assert "scorer" not in summary["goals"][0]
    (clock,) = summary["clock"]
    assert clock["start_ms"] == 0 and clock["start_clock_s"] == 120
    assert reader.calls < 40  # read on change, not on every frame

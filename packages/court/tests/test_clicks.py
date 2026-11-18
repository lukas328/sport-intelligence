import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from handball_court import clicks as courtclicks
from handball_court.clicks import ClicksError

DATA = json.loads((Path(__file__).parent / "data" / "court_clicks.json").read_text())
SIZE = (1280, 720)


def _camera() -> np.ndarray:
    """Court -> image of a camera beside the near sideline looking at the left goal area."""
    return np.array([[38.0, 20.0, 150.0], [-2.0, -14.0, 560.0], [0.004, 0.035, 1.0]])


def _on(h: np.ndarray, name: str, ts: list[float]) -> list[tuple[float, float]]:
    c = courtclicks._DENSE[name]
    pts = courtclicks._project(h, c[[int(t * (len(c) - 1)) for t in ts]])
    return [(float(x), float(y)) for x, y in pts]


def _to_court(h: np.ndarray, px: np.ndarray) -> np.ndarray:
    return courtclicks._project(np.linalg.inv(h), np.asarray(px, float))


def _grid_px(h: np.ndarray) -> np.ndarray:
    g = np.array([(x, y) for x in range(0, 21, 2) for y in range(0, 21, 2)], float)
    return courtclicks._project(h, g)


def test_lines_and_arc_fix_the_court_where_straight_lines_leave_it_open() -> None:
    # both sidelines and the goal line fix only 6 of 8 degrees of freedom; the 6 m arc decides
    h = _camera()
    lines = {
        "side_near": _on(h, "side_near", [0.05, 0.15, 0.3]),
        "side_far": _on(h, "side_far", [0.05, 0.2, 0.35]),
        "goal_left": _on(h, "goal_left", [0.3, 0.7]),
        "six_left": _on(h, "six_left", [0.2, 0.5, 0.8]),
    }
    fit = courtclicks.fit_clicks({}, lines, SIZE)
    assert fit.median_px < 0.5
    assert np.abs(_grid_px(fit.homography) - _grid_px(h)).max() < 1.0


def test_noisy_clicks_still_give_the_court() -> None:
    h = _camera()
    rng = np.random.default_rng(1)

    def noisy(ps: list[tuple[float, float]]) -> list[tuple[float, float]]:
        return [(x + rng.normal(0, 2), y + rng.normal(0, 2)) for x, y in ps]

    lines = {
        "side_near": noisy(_on(h, "side_near", [0.05, 0.15, 0.3])),
        "side_far": noisy(_on(h, "side_far", [0.05, 0.2, 0.35])),
        "goal_left": noisy(_on(h, "goal_left", [0.3, 0.5, 0.7])),
        "six_left": noisy(_on(h, "six_left", [0.2, 0.5, 0.8])),
    }
    fit = courtclicks.fit_clicks({}, lines, SIZE)
    # court positions near the clicks within a few decimetres
    g = np.array([(x, y) for x in range(0, 9) for y in range(2, 19, 2)], float)
    back = _to_court(fit.homography, courtclicks._project(h, g))
    assert np.median(np.linalg.norm(back - g, axis=1)) < 0.3


@pytest.mark.parametrize(
    "frame", [f for f in DATA["frames"] if "expected_court_to_image" in f], ids=lambda f: f["frame"]
)
def test_owner_clicks_give_the_same_court_as_the_test_set_truth(frame: dict[str, Any]) -> None:
    lines = {k: [tuple(p) for p in v] for k, v in frame["lines"].items()}
    points = {k: tuple(v) for k, v in frame["points"].items()}
    fit = courtclicks.fit_clicks(points, lines, tuple(frame["image_size"]))
    expected = np.array(frame["expected_court_to_image"])
    clicks = np.array([*points.values(), *[p for c in lines.values() for p in c]])
    # compare where both put the court near the clicks (the truth holds there)
    back_fit = _to_court(fit.homography, clicks)
    back_exp = _to_court(expected, clicks)
    assert np.abs(back_fit - back_exp).max() < 0.3  # the truth itself holds to 0.3 m
    assert fit.median_px <= frame["expected_median_px"] + 0.3


def test_one_click_on_a_neighbouring_line_is_dropped() -> None:
    frame = next(f for f in DATA["frames"] if f["frame"] == "c012_00170")
    lines = {k: [tuple(p) for p in v] for k, v in frame["lines"].items()}
    points = {k: tuple(v) for k, v in frame["points"].items()}
    fit = courtclicks.fit_clicks(points, lines, SIZE)
    assert len(fit.dropped) >= 1
    assert len(fit.clicks) == len(fit.residual_px)
    assert not set(fit.dropped) & set(fit.clicks)
    assert all(d.kind in ("point", "line") for d in fit.dropped)
    assert fit.median_px <= courtclicks.MAX_MEDIAN_PX


def test_too_few_clicks_are_refused() -> None:
    h = _camera()
    lines = {
        "side_near": _on(h, "side_near", [0.1, 0.3]),
        "goal_left": _on(h, "goal_left", [0.3, 0.7]),
    }
    with pytest.raises(ClicksError, match="too few clicks") as exc:
        courtclicks.fit_clicks({"corner_tl": (500.0, 300.0)}, lines, SIZE)
    assert exc.value.code == "too_few"


def test_clicks_that_disagree_are_refused() -> None:
    h = _camera()
    lines = {
        "side_near": _on(h, "side_near", [0.05, 0.15, 0.3]),
        "side_far": _on(h, "side_far", [0.05, 0.2, 0.35]),
        # the 9 m clicks put on the 6 m line: no court explains both
        "goal_left": _on(h, "goal_left", [0.3, 0.7]),
        "nine_left": _on(h, "six_left", [0.2, 0.4, 0.6, 0.8]),
        "six_left": _on(h, "nine_left", [0.2, 0.4, 0.6, 0.8]),
    }
    with pytest.raises(ClicksError, match="do not agree") as exc:
        courtclicks.fit_clicks({}, lines, SIZE)
    assert exc.value.code == "disagree" and exc.value.worst is not None
    assert exc.value.worst.kind == "line" and exc.value.worst.name in lines
    assert exc.value.worst_px is not None and exc.value.worst_px > courtclicks.MAX_CLICK_PX


def test_unknown_names_are_refused() -> None:
    with pytest.raises(ClicksError, match="unknown"):
        courtclicks.fit_clicks({"middle_of_nowhere": (1.0, 1.0)}, {}, SIZE)


def test_court_model_lists_every_clickable_line_and_point() -> None:
    model = courtclicks.court_model()
    lines = model["lines"]
    assert isinstance(lines, dict)
    assert set(lines) == set(courtclicks.LINES)
    assert lines["side_near"] == {"kind": "line", "court": [[0.0, 0.0], [40.0, 0.0]]}
    six = lines["six_left"]["court"]
    assert all(abs(np.hypot(x, max(0, abs(y - 10) - 1.5)) - 6) < 0.01 for x, y in six)
    assert model["points"]["corner_tl"] == list(courtclicks.KEYPOINTS["corner_tl"])


def test_a_dropped_click_that_leaves_two_courts_is_refused() -> None:
    # sidelines, one goal line and the centre line fix the court with two clicks each; a third
    # centre-line click 6 m off makes two courts: one with each pair of centre clicks
    h = np.array([[30.0, 12.0, 80.0], [-1.0, -14.0, 640.0], [0.0005, 0.012, 1.0]])
    c = courtclicks._DENSE

    def on(name: str, ts: list[float]) -> list[tuple[float, float]]:
        d = c[name]
        pts = courtclicks._project(h, d[[int(t * (len(d) - 1)) for t in ts]])
        return [(float(x), float(y)) for x, y in pts]

    off = courtclicks._project(h, np.array([[26.0, 14.0]]))[0]
    lines = {
        "side_near": on("side_near", [0.1, 0.5, 0.9]),
        "side_far": on("side_far", [0.1, 0.5, 0.9]),
        "goal_left": on("goal_left", [0.3, 0.7]),
        "centre": [*on("centre", [0.2, 0.8]), (float(off[0]), float(off[1]))],
    }
    with pytest.raises(ClicksError, match="two different courts") as exc:
        courtclicks.fit_clicks({}, lines, SIZE)
    assert exc.value.code == "disagree"
    assert exc.value.worst is not None and exc.value.worst.name == "centre"

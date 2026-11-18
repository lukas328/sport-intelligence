import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from handball_vision import courtclicks
from handball_vision.calibration import Calibration, CalibrationError

DATA = json.loads((Path(__file__).parent / "data" / "court_clicks.json").read_text())
SIZE = (1280, 720)


def _camera() -> np.ndarray:
    """Court -> image of a camera beside the near sideline looking at the left goal area."""
    return np.array([[38.0, 20.0, 150.0], [-2.0, -14.0, 560.0], [0.004, 0.035, 1.0]])


def _on(h: np.ndarray, name: str, ts: list[float]) -> list[tuple[float, float]]:
    c = courtclicks._DENSE[name]
    pts = courtclicks._project(h, c[[int(t * (len(c) - 1)) for t in ts]])
    return [(float(x), float(y)) for x, y in pts]


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
    fit = courtclicks.calibrate_clicks({}, lines, SIZE)
    assert fit.calibration.reprojection_px < 0.5
    assert np.abs(_grid_px(fit.calibration.homography) - _grid_px(h)).max() < 1.0


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
    fit = courtclicks.calibrate_clicks({}, lines, SIZE)
    # court positions near the clicks within a few decimetres
    g = np.array([(x, y) for x in range(0, 9) for y in range(2, 19, 2)], float)
    back = fit.calibration.to_court(courtclicks._project(h, g))
    assert np.median(np.linalg.norm(back - g, axis=1)) < 0.3


@pytest.mark.parametrize(
    "frame", [f for f in DATA["frames"] if "expected_court_to_image" in f], ids=lambda f: f["frame"]
)
def test_owner_clicks_give_the_same_court_as_the_test_set_truth(frame: dict[str, Any]) -> None:
    lines = {k: [tuple(p) for p in v] for k, v in frame["lines"].items()}
    points = {k: tuple(v) for k, v in frame["points"].items()}
    fit = courtclicks.calibrate_clicks(points, lines, tuple(frame["image_size"]))
    expected = np.array(frame["expected_court_to_image"])
    clicks = np.array([*points.values(), *[p for c in lines.values() for p in c]])
    # compare where both put the court near the clicks (the truth holds there)
    back_fit = fit.calibration.to_court(clicks)
    back_exp = Calibration(expected, 1.0, 0.0, "user_correction", SIZE).to_court(clicks)
    assert np.abs(back_fit - back_exp).max() < 0.3  # the truth itself holds to 0.3 m
    assert fit.calibration.reprojection_px <= frame["expected_median_px"] + 0.3


def test_one_click_on_a_neighbouring_line_is_dropped() -> None:
    frame = next(f for f in DATA["frames"] if f["frame"] == "c012_00170")
    lines = {k: [tuple(p) for p in v] for k, v in frame["lines"].items()}
    points = {k: tuple(v) for k, v in frame["points"].items()}
    fit = courtclicks.calibrate_clicks(points, lines, SIZE)
    assert fit.dropped >= 1
    assert fit.calibration.reprojection_px <= courtclicks.MAX_MEDIAN_PX


def test_too_few_clicks_are_refused() -> None:
    h = _camera()
    lines = {
        "side_near": _on(h, "side_near", [0.1, 0.3]),
        "goal_left": _on(h, "goal_left", [0.3, 0.7]),
    }
    with pytest.raises(CalibrationError, match="too few clicks"):
        courtclicks.calibrate_clicks({"corner_tl": (500.0, 300.0)}, lines, SIZE)


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
    with pytest.raises(CalibrationError, match="do not agree"):
        courtclicks.calibrate_clicks({}, lines, SIZE)


def test_unknown_names_are_refused() -> None:
    with pytest.raises(CalibrationError, match="unknown"):
        courtclicks.calibrate_clicks({"middle_of_nowhere": (1.0, 1.0)}, {}, SIZE)

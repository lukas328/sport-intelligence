import numpy as np
import pytest

from handball_court import clicks
from handball_vision import courtclicks
from handball_vision.calibration import CalibrationError

SIZE = (1280, 720)


def _on(h: np.ndarray, name: str, ts: list[float]) -> list[tuple[float, float]]:
    c = clicks._DENSE[name]
    pts = clicks._project(h, c[[int(t * (len(c) - 1)) for t in ts]])
    return [(float(x), float(y)) for x, y in pts]


def test_clicks_give_a_user_correction_calibration() -> None:
    h = np.array([[38.0, 20.0, 150.0], [-2.0, -14.0, 560.0], [0.004, 0.035, 1.0]])
    lines = {
        "side_near": _on(h, "side_near", [0.05, 0.15, 0.3]),
        "side_far": _on(h, "side_far", [0.05, 0.2, 0.35]),
        "goal_left": _on(h, "goal_left", [0.3, 0.7]),
        "six_left": _on(h, "six_left", [0.2, 0.5, 0.8]),
    }
    fit = courtclicks.calibrate_clicks({}, lines, SIZE)
    assert fit.calibration.source == "user_correction"
    assert fit.calibration.image_size == SIZE
    assert fit.calibration.reprojection_px < 0.5
    court = np.array([[0.0, 0.0], [6.0, 10.0], [9.0, 4.0]])
    assert np.abs(fit.calibration.to_court(fit.calibration.to_image(court)) - court).max() < 1e-6
    assert np.abs(fit.calibration.to_image(court) - clicks._project(h, court)).max() < 1.0


def test_refusals_are_calibration_errors() -> None:
    with pytest.raises(CalibrationError, match="unknown"):
        courtclicks.calibrate_clicks({"middle_of_nowhere": (1.0, 1.0)}, {}, SIZE)

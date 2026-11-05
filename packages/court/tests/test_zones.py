import json
from pathlib import Path

import pytest

from handball_court.zones import mirror_goal_zone, shot_zone

CASES = json.loads(
    (Path(__file__).resolve().parent.parent / "spec" / "zone_cases.json").read_text()
)["cases"]


@pytest.mark.parametrize("case", CASES)
def test_shared_cases(case: dict[str, object]) -> None:
    got = shot_zone(
        float(case["x"]),  # type: ignore[arg-type]
        float(case["y"]),  # type: ignore[arg-type]
        penalty=bool(case.get("penalty")),
        fast_break=bool(case.get("fast_break")),
        empty_goal=bool(case.get("empty_goal")),
    )
    assert got == case["zone"]


def test_mirror() -> None:
    assert mirror_goal_zone("ML") == "MR"
    assert mirror_goal_zone("TC") == "TC"
    with pytest.raises(ValueError):
        mirror_goal_zone("XX")

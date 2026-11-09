"""Game clock text ("mm:ss") shared by official reports, goal candidates and feeds."""

from __future__ import annotations

import pytest

from handball_api.core.clock import format_clock, parse_clock
from handball_api.integrations.base import AdapterError
from handball_api.integrations.official_feed import parse_clock as feed_clock


def test_format_clock() -> None:
    assert format_clock(None) is None
    assert format_clock(0) == "00:00"
    assert format_clock(65.9) == "01:05"  # whole seconds, not rounded
    assert format_clock(3600) == "60:00"
    assert format_clock(3725) == "62:05"  # overtime


@pytest.mark.parametrize(
    ("text", "seconds"),
    [("05:12", 312), ("0:07", 7), ("100:00", 6000), (" 31:00 ", 1860), ("42", 42.0), ("7.5", 7.5)],
)
def test_parse_clock(text: str, seconds: float) -> None:
    assert parse_clock(text) == seconds
    assert feed_clock(text) == seconds


@pytest.mark.parametrize("text", ["12:5", "12:30.5", "1:2:3", "x:y", "", "mm:ss"])
def test_parse_clock_rejects(text: str) -> None:
    with pytest.raises(ValueError):
        parse_clock(text)
    with pytest.raises(AdapterError, match="Invalid clock"):
        feed_clock(text)

"""Game clock as text: "mm:ss" as official reports and feeds write it."""

from __future__ import annotations

import re

_MM_SS = re.compile(r"(\d{1,3}):(\d{2})")


def format_clock(clock_s: float | None) -> str | None:
    """Seconds of the game clock as "mm:ss" (whole seconds, minutes past 60 in overtime)."""
    if clock_s is None:
        return None
    c = int(clock_s)
    return f"{c // 60:02d}:{c % 60:02d}"


def parse_clock(value: str) -> float:
    """Parse "mm:ss" (minutes 1 to 3 digits, seconds 2 digits) or plain seconds.

    Raises ValueError otherwise; "12:5" or "12:30.5" are not accepted (the stricter of the two
    parsers this replaces: the feed adapter also took fractional seconds)."""
    v = value.strip()
    m = _MM_SS.fullmatch(v)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    return float(v)

"""What every official report parser returns, and the small helpers they share."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from dataclasses import replace as dc_replace
from typing import Any

HANDBALL_CH = "handball_ch"
DHB = "dhb"
NULIGA = "nuliga"
HLA = "hla"
PROVIDERS = (HANDBALL_CH, DHB, NULIGA, HLA)
ID_PROVIDERS = (HANDBALL_CH, DHB, HLA)  # a plain game id names the game (nuLiga needs the host)
CLOCK = re.compile(r"(\d{1,2}):(\d{2})")


@dataclass(frozen=True)
class OfficialEntry:
    clock_s: int  # match second, 0..3600 (second half continues at 30:00)
    kind: str  # goal, penalty_goal, shot_saved, shot_missed, shot_post, penalty_saved, ...
    team: str | None  # home | away
    number: int | None = None
    name: str | None = None
    score: tuple[int, int] | None = None  # home, away after the entry
    goalkeeper_number: int | None = None  # saves: the keeper of the other team


@dataclass
class OfficialReport:
    provider: str
    game_id: int
    source_url: str
    home: str | None = None
    away: str | None = None
    competition: str | None = None
    date: str | None = None
    final: tuple[int, int] | None = None
    half_time: tuple[int, int] | None = None
    entries: list[OfficialEntry] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # shown as warnings of the import


@dataclass(frozen=True)
class ReportLink:
    """The one report to fetch: built from the checked parts of the given link."""

    provider: str
    game_id: int
    url: str
    pdf: bool = False


def without_opponent_names(report: OfficialReport, is_home: bool) -> OfficialReport:
    """Numbers only for the other team (clubs not verified yet see no names of other teams'
    players, services/org_verification.py)."""
    opponent = "away" if is_home else "home"
    return dc_replace(
        report,
        entries=[dc_replace(e, name=None) if e.team == opponent else e for e in report.entries],
    )


def parse_number(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return int(value) if isinstance(value, str) and value.strip().isdigit() else None


def parse_score(value: Any) -> tuple[int, int] | None:
    m = re.fullmatch(r"\s*(\d+)\s*:\s*(\d+)\s*", str(value or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


def parse_clock(value: str) -> int | None:
    m = CLOCK.fullmatch(value.strip())
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None

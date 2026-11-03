"""Match format templates (addendum 01, 4.8). A match stores the resolved period length and count,
so the clock stays right even if a template changes later.

Sources: IHF rules (adults 2 x 30 min) and Swiss Handball youth regulations (U15/U17 2 x 25,
U13 2 x 20, minihandball and tournaments with short games). Values are defaults; clubs can enter
their own format per match.
"""

from __future__ import annotations

from dataclasses import dataclass

from handball_api.models.enums import MatchFormatKey


@dataclass(frozen=True)
class FormatTemplate:
    key: MatchFormatKey
    period_s: int
    periods: int
    court: str
    youth: bool


TEMPLATES: dict[MatchFormatKey, FormatTemplate] = {
    t.key: t
    for t in (
        FormatTemplate(MatchFormatKey.ADULT_2X30, 1800, 2, "40x20", youth=False),
        FormatTemplate(MatchFormatKey.YOUTH_2X25, 1500, 2, "40x20", youth=True),
        FormatTemplate(MatchFormatKey.YOUTH_2X20, 1200, 2, "40x20", youth=True),
        FormatTemplate(MatchFormatKey.MINI, 600, 2, "20x13", youth=True),
        FormatTemplate(MatchFormatKey.TOURNAMENT, 600, 1, "40x20", youth=False),
    )
}


def resolve(
    key: MatchFormatKey, period_s: int | None = None, periods: int | None = None
) -> tuple[str, int, int]:
    """(format key, period length in s, number of periods); custom needs explicit values."""
    if key == MatchFormatKey.CUSTOM:
        if not period_s or not periods:
            raise ValueError("custom format needs period_s and periods")
        return key.value, period_s, periods
    t = TEMPLATES[key]
    return key.value, period_s or t.period_s, periods or t.periods


def default_for(is_youth: bool) -> MatchFormatKey:
    return MatchFormatKey.YOUTH_2X25 if is_youth else MatchFormatKey.ADULT_2X30

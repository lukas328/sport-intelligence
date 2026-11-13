"""Official match reports imported into a match (source "official_report").

The sources (handball.ch, DHB, nuLiga, HLA), where each report is fetched and how it is read are
in integrations/official_reports; the comparison of the official goals with the video and the
coach's check of it in services/official_comparison.py. This module fetches a report and stores
it in a match.

`apply` stores the log as events of the match. Rules:
- a re-import replaces the earlier official_report events of the match;
- home/away become own/opponent via `match.is_home`; own players are linked by shirt number;
- the match minute is the clock: the first half is before `match.period_s` (30:00 in adults);
  an event exactly at the end of the half belongs to it while the score is the half-time score;
- goals are matched with the goals already stored, same side, at most 20 s of match clock apart:
  * a goal a person entered (tagging, feed, correction) wins: no official goal is added for it;
  * an automatic goal (score overlay, heuristic, a confirmed goal candidate) is the same goal
    seen on video: the official goal takes over its video time and shot position
    (attributes.video keeps what the video read) and the automatic row is dropped, so nothing is
    counted twice. Automatic goals without an official counterpart are kept when read from the
    overlay or confirmed by the coach (they show where the video and the report disagree) and
    dropped when only estimated (heuristic);
  * the other shots (saves, misses) the same way against the shots the coach confirmed on a
    shot candidate (same side and outcome): the official entry takes over the video time and the
    candidate now points to it; an entry confirmed on the video before a re-import keeps it;
  * entries without a video time from the video get theirs from the match clock
    (match_clock: the overlay clock of the analysis, entries with a known video time, the
    throw-offs), not counted linearly from the throw-off of the half;
  * suspensions, time-outs and the other entries are added as they are.

The fetch functions below are the ones the import calls (tests replace them, and `_pdf_text`,
on this module); they hand over to the integration modules.
"""

from __future__ import annotations

import contextlib
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import delete, select

from handball_api.core.clock import format_clock
from handball_api.core.errors import ProblemError
from handball_api.integrations.official_reports import detect, locate
from handball_api.integrations.official_reports import dhb as _dhb
from handball_api.integrations.official_reports import hla as _hla
from handball_api.integrations.official_reports import nuliga as _nuliga
from handball_api.integrations.official_reports.base import (
    DHB,
    HANDBALL_CH,
    HLA,
    ID_PROVIDERS,
    NULIGA,
    PROVIDERS,
    OfficialEntry,
    OfficialReport,
    ReportLink,
    without_opponent_names,
)
from handball_api.integrations.official_reports.dhb import DHB_PDF, parse_dhb
from handball_api.integrations.official_reports.handball_ch import (
    CH_PAGE,
    fetch_handball_ch,
    parse_handball_ch,
)
from handball_api.integrations.official_reports.hla import HLA_NOTE, HLA_PDF, parse_hla
from handball_api.integrations.official_reports.http import pdf_text as _pdf_text
from handball_api.integrations.official_reports.nuliga import (
    NULIGA_HOST,
    parse_nuliga,
    parse_nuliga_pdf,
)
from handball_api.models import Event, GoalCandidate, Match, Opponent
from handball_api.services import audit, match_clock, org_verification, timeline
from handball_api.services.auto_events import CANDIDATE, OVERLAY
from handball_api.services.context import Ctx
from handball_api.services.events import video_from_clock
from handball_api.services.matches import get_match
from handball_api.services.official_comparison import (
    AUTO_GOALS,
    MATCH_WINDOW_S,
    REVIEW,
    SOURCE,
    Seen,
    comparison,
    nearest,
    review,
)
from handball_api.services.policies import Action
from handball_api.services.roster import numbers as roster_numbers

__all__ = [
    "AUTO_GOALS",
    "CH_PAGE",
    "DHB",
    "DHB_PDF",
    "HANDBALL_CH",
    "HLA",
    "HLA_NOTE",
    "HLA_PDF",
    "ID_PROVIDERS",
    "MATCH_WINDOW_S",
    "NULIGA",
    "NULIGA_HOST",
    "PROVIDERS",
    "REVIEW",
    "SOURCE",
    "OfficialEntry",
    "OfficialReport",
    "ReportLink",
    "_pdf_text",
    "apply",
    "comparison",
    "detect",
    "fetch",
    "fetch_dhb",
    "fetch_handball_ch",
    "fetch_hla",
    "fetch_nuliga",
    "import_report",
    "locate",
    "parse_dhb",
    "parse_handball_ch",
    "parse_hla",
    "parse_nuliga",
    "parse_nuliga_pdf",
    "review",
    "without_opponent_names",
]


# ---- fetch ---------------------------------------------------------------------------------
# `_pdf_text` and the fetch functions are looked up on this module when called, so a test that
# replaces one of them here replaces it for the import.


async def fetch_dhb(match_id: int) -> str:
    """Text of a DHB press report (replaced by recorded text in tests)."""
    return await _dhb.fetch_dhb(match_id, _pdf_text)


async def fetch_nuliga(link: ReportLink) -> str:
    """HTML of a nuLiga game report, or the text of its PDF (replaced by recorded data in
    tests)."""
    return await _nuliga.fetch_nuliga(link, _pdf_text)


async def fetch_hla(match_id: int) -> str:
    """Text of an HLA match report PDF (replaced by recorded text in tests)."""
    return await _hla.fetch_hla(match_id, _pdf_text)


async def fetch(source: str, provider: str | None = None) -> OfficialReport:
    link = locate(source, provider)
    if link.provider == HANDBALL_CH:
        report = parse_handball_ch(link.game_id, await fetch_handball_ch(link.game_id))
    elif link.provider == DHB:
        report = parse_dhb(link.game_id, await fetch_dhb(link.game_id))
    elif link.provider == NULIGA:
        page = await fetch_nuliga(link)
        report = (
            parse_nuliga_pdf(link.game_id, link.url, page)
            if link.pdf
            else parse_nuliga(link.game_id, link.url, page)
        )
    else:
        report = parse_hla(link.game_id, await fetch_hla(link.game_id))
    # the HLA report has no timed goals: its result alone is still worth importing
    if not report.entries and not (report.provider == HLA and report.final):
        raise ProblemError(
            422, "report-empty", "The report has no game log yet (not played or no live ticker)"
        )
    return report


# ---- apply to a match ----------------------------------------------------------------------

# kind -> event fields
_EVENTS: dict[str, dict[str, str]] = {
    "goal": {"type": "shot", "outcome": "goal"},
    "shot_saved": {"type": "shot", "outcome": "save"},
    "shot_missed": {"type": "shot", "outcome": "miss"},
    "shot_post": {"type": "shot", "outcome": "post"},
    "penalty_goal": {"type": "shot", "outcome": "goal", "shot_type": "penalty"},
    "penalty_saved": {"type": "shot", "outcome": "save", "shot_type": "penalty"},
    "penalty_missed": {"type": "shot", "outcome": "miss", "shot_type": "penalty"},
    "penalty_post": {"type": "shot", "outcome": "post", "shot_type": "penalty"},
    "turnover": {"type": "turnover"},
    "suspension": {"type": "suspension_2min"},
    "warning": {"type": "yellow_card"},
    "disqualification": {"type": "red_card"},
    "timeout": {"type": "timeout"},
}


def _candidate_of(e: Event) -> str | None:
    """The candidate an event was confirmed on: its own event, or a report entry it pinned."""
    attrs = e.attributes or {}
    v = attrs.get("video")
    if isinstance(v, dict) and v.get("candidate_id"):
        return str(v["candidate_id"])
    c = attrs.get("goal_candidate")
    return str(c) if c else None


def _period(e: OfficialEntry, period_s: int, half_time: tuple[int, int] | None) -> int:
    if e.clock_s < period_s:
        return 1
    # an entry right at the end of the half (a last goal at 30:00): first half while the score
    # is still the half-time score
    at_end = e.clock_s == period_s and half_time is not None
    if at_end and (e.score is None or sum(e.score) <= sum(half_time or (0, 0))):
        return 1
    return 2


def _words(name: str | None) -> set[str]:
    return {w for w in re.split(r"[^\w]+", (name or "").casefold()) if len(w) >= 4}


async def _analysis(ctx: Ctx, match: Match) -> dict[str, Any] | None:
    """The analysis of the match's timeline (its overlay clock maps the report), over all parts."""
    return await timeline.clock_analysis(ctx, match.id)


def _clock_time(cm: match_clock.ClockMap, match: Match, period: int, clock: float) -> int | None:
    t, _ = cm.video_ms(period, clock) if period in (1, 2) else (None, None)
    return t if t is not None else video_from_clock(match, period, clock)


@dataclass
class _Known:
    """What the match had before the import: the goals and shots the report is matched with."""

    replaced: int  # official events of an earlier import, now deleted
    reviewed: dict[tuple[str, float | None], Any]  # the coach's check of an earlier official goal
    seen: list[Seen]  # goals and confirmed shots from video (automatic or an earlier import)
    manual: list[Seen]  # goals a person entered
    auto: list[Event]  # automatic goals
    confirmed_shots: list[Event]  # saves and misses confirmed on a shot candidate


@dataclass
class _Added:
    """The report's entries added as events, and what they were matched with."""

    created: int = 0
    matched: int = 0
    kept_manual: int = 0
    skipped: int = 0
    unknown_numbers: set[int] = field(default_factory=set)
    used: set[int] = field(default_factory=set)  # ids of matched candidates
    relink: list[tuple[str, Event]] = field(default_factory=list)  # candidate -> official event


async def _known(ctx: Ctx, match: Match) -> _Known:
    """Reads what the match has and deletes the official events of an earlier import (their
    video data and the coach's check are kept to be matched again)."""
    previous = (
        await ctx.db.scalars(
            select(Event).where(Event.match_id == match.id, Event.source == SOURCE)
        )
    ).all()
    seen: list[Seen] = []
    reviewed = {  # the coach's check of a goal survives a re-import of the same report
        (p.side, p.clock_s): r
        for p in previous
        if p.outcome == "goal" and (r := (p.attributes or {}).get("review")) in REVIEW
    }
    for p in previous:  # video data an earlier import took over: matched again below
        v = (p.attributes or {}).get("video")
        if isinstance(v, dict) and v.get("clock_s") is not None:
            seen.append(
                Seen(
                    side=p.side,
                    clock_s=float(v["clock_s"]),
                    t_ms=v.get("t_ms"),
                    x=p.x,
                    y=p.y,
                    source=str(v.get("source", OVERLAY)),
                    confidence=float(v.get("confidence", 0.9)),
                    outcome=p.outcome or "goal",
                    candidate_id=_candidate_of(p),
                )
            )
    await ctx.db.execute(delete(Event).where(Event.match_id == match.id, Event.source == SOURCE))
    goals = (
        await ctx.db.scalars(
            select(Event).where(
                Event.match_id == match.id, Event.type == "shot", Event.outcome == "goal"
            )
        )
    ).all()
    auto = [g for g in goals if g.source in AUTO_GOALS]
    seen += [
        Seen(
            g.side,
            float(g.clock_s),
            g.t_ms,
            g.x,
            g.y,
            g.source,
            g.confidence,
            g,
            candidate_id=_candidate_of(g),
        )
        for g in auto
        if g.clock_s is not None
    ]
    # saves and misses the coach confirmed on a shot candidate: matched like automatic goals
    confirmed_shots = (
        await ctx.db.scalars(
            select(Event).where(
                Event.match_id == match.id,
                Event.type == "shot",
                Event.outcome != "goal",
                Event.source == CANDIDATE,
                Event.clock_s.is_not(None),
            )
        )
    ).all()
    seen += [
        Seen(
            g.side,
            float(g.clock_s or 0.0),
            g.t_ms,
            g.x,
            g.y,
            g.source,
            g.confidence,
            g,
            outcome=g.outcome or "miss",
            candidate_id=_candidate_of(g),
        )
        for g in confirmed_shots
    ]
    manual = [
        Seen(g.side, float(g.clock_s), g.t_ms, g.x, g.y, g.source, g.confidence, g)
        for g in goals
        if g.source not in AUTO_GOALS and g.clock_s is not None
    ]
    return _Known(
        replaced=len(previous),
        reviewed=reviewed,
        seen=seen,
        manual=manual,
        auto=auto,
        confirmed_shots=list(confirmed_shots),
    )


def _video_attrs(c: Seen) -> dict[str, Any]:
    """What the video read, kept in attributes.video of the official entry that took it over."""
    return {
        "source": c.source,
        "clock_s": c.clock_s,
        "t_ms": c.t_ms,
        "confidence": round(c.confidence, 3),
        **({"candidate_id": c.candidate_id} if c.candidate_id else {}),
    }


def _add_entries(
    ctx: Ctx,
    match: Match,
    report: OfficialReport,
    known: _Known,
    clock_map: match_clock.ClockMap,
    roster: dict[int, uuid.UUID],
) -> _Added:
    """Adds each entry of the report as an event, matched with the goals and shots from video."""
    own_team = "home" if match.is_home else "away"
    seen = known.seen
    out = _Added()
    used = out.used
    for e in report.entries:
        spec = _EVENTS.get(e.kind)
        if spec is None or e.team is None:
            out.skipped += 1
            continue
        side = "own" if e.team == own_team else "opponent"
        period = _period(e, match.period_s, report.half_time)
        clock = float(e.clock_s)
        attrs: dict[str, Any] = {"official_time": format_clock(e.clock_s)}
        if e.name:
            attrs["name"] = e.name[:80]
        if e.score:
            attrs["score"] = list(e.score if own_team == "home" else e.score[::-1])
        t_ms, x, y = _clock_time(clock_map, match, period, clock), None, None
        pinned: Seen | None = None
        if spec.get("type") == "shot" and spec.get("outcome") != "goal":
            pinned = nearest(
                [c for c in seen if id(c) not in used], side, clock, str(spec["outcome"])
            )
            if pinned is not None:
                used.add(id(pinned))
                if pinned.t_ms is not None:
                    t_ms = int(pinned.t_ms)
                attrs["video"] = _video_attrs(pinned)
        if spec.get("outcome") == "goal":
            free = [c for c in known.manual if id(c) not in used]
            hit = nearest(free, side, clock)
            if hit is not None:  # entered by a person: theirs wins
                used.add(id(hit))
                out.kept_manual += 1
                continue
            vid = nearest([c for c in seen if id(c) not in used], side, clock)
            if vid is not None:
                used.add(id(vid))
                out.matched += 1
                if vid.t_ms is not None:
                    t_ms = int(vid.t_ms)
                x, y = vid.x, vid.y
                attrs["video"] = _video_attrs(vid)
                pinned = vid
            if (side, clock) in known.reviewed:
                attrs["review"] = known.reviewed[(side, clock)]
        if spec.get("outcome") == "save" and e.goalkeeper_number is not None:
            gk = roster.get(e.goalkeeper_number) if side == "opponent" else None
            attrs.update(
                {"goalkeeper_id": str(gk)} if gk else {"goalkeeper_number": e.goalkeeper_number}
            )
        player = roster.get(e.number) if side == "own" and e.number is not None else None
        if side == "own" and e.number is not None and player is None:
            out.unknown_numbers.add(e.number)
        new = Event(
            organization_id=match.organization_id,
            match_id=match.id,
            type=spec["type"],
            side=side,
            period=period,
            clock_s=clock,
            t_ms=t_ms,
            number=e.number,
            player_id=player,
            outcome=spec.get("outcome"),
            shot_type=spec.get("shot_type"),
            shot_zone="penalty" if spec.get("shot_type") == "penalty" else None,
            x=x,
            y=y,
            source=SOURCE,
            confidence=1.0,
            attributes=attrs,
        )
        ctx.db.add(new)
        if pinned is not None and pinned.candidate_id:
            out.relink.append((pinned.candidate_id, new))
        out.created += 1
    return out


async def _settle_video_goals(ctx: Ctx, match: Match, known: _Known, added: _Added) -> int:
    """Drops the automatic goals and confirmed shots an official entry took over (and the
    estimates without a counterpart) and points the candidates to the official entries. Returns
    the number of video goals kept without an official counterpart."""
    # automatic goals: the matched ones are now official goals; estimates without a counterpart
    # are dropped (the report has every goal), overlay readings and goals the coach confirmed
    # from a candidate without one stay for checking
    taken = {id(c.event) for c in known.seen if c.event is not None and id(c) in added.used}
    unmatched_video = 0
    for g in known.auto:
        if id(g) in taken or g.source not in (OVERLAY, CANDIDATE):
            await ctx.db.delete(g)
        else:
            unmatched_video += 1
    for g in known.confirmed_shots:  # the official entry took over: one shot, not two
        if id(g) in taken:
            await ctx.db.delete(g)
    await ctx.db.flush()
    for cand_id, ev in added.relink:  # the candidate now points to the official entry
        with contextlib.suppress(ValueError):
            c = await ctx.db.get(GoalCandidate, uuid.UUID(cand_id))
            if c is not None and c.match_id == match.id and c.status == "confirmed":
                c.event_id = ev.id
    return unmatched_video


async def _write_result(
    ctx: Ctx,
    match: Match,
    report: OfficialReport,
    known: _Known,
    added: _Added,
    unmatched_video: int,
) -> dict[str, Any]:
    """Stores the result and the report's source on the match, audits the import and returns
    its summary with the warnings."""
    own_team = "home" if match.is_home else "away"
    warnings: list[str] = list(report.notes)
    final = report.final
    if final is not None:
        own, opp = final if own_team == "home" else final[::-1]
        half = report.half_time
        if match.score_own is None and match.score_opponent is None:
            match.score_own, match.score_opponent = own, opp
            if half is not None and match.halftime_own is None:
                match.halftime_own, match.halftime_opponent = (
                    half if own_team == "home" else half[::-1]
                )
        elif (match.score_own, match.score_opponent) != (own, opp):
            warnings.append(
                f"stored result {match.score_own}:{match.score_opponent} differs from the "
                f"report ({own}:{opp})"
            )
    if added.unknown_numbers:
        warnings.append(f"numbers not in the roster: {sorted(added.unknown_numbers)}")
    opp_name = (
        await ctx.db.scalar(select(Opponent.name).where(Opponent.id == match.opponent_id))
        if match.opponent_id
        else None
    )
    their = report.away if own_team == "home" else report.home
    ours = report.home if own_team == "home" else report.away
    if opp_name and not _words(opp_name) & _words(their) and _words(opp_name) & _words(ours):
        warnings.append(
            f"'{opp_name}' is the {own_team} team in the report: check home/away of the match"
        )
    match.report_extra = {
        **(match.report_extra or {}),
        "official_report": {
            "provider": report.provider,
            "game_id": report.game_id,
            "url": report.source_url,
            "home": report.home,
            "away": report.away,
        },
    }
    await ctx.db.flush()
    result = {
        "provider": report.provider,
        "game_id": report.game_id,
        "source_url": report.source_url,
        "home": report.home,
        "away": report.away,
        "final": list(report.final) if report.final else None,
        "created": added.created,
        "replaced": known.replaced,
        "matched_video_goals": added.matched,
        "unmatched_video_goals": unmatched_video,
        "kept_manual_goals": added.kept_manual,
        "skipped": added.skipped,
        "warnings": warnings,
    }
    await audit.record(
        ctx,
        "match.official_report_imported",
        target_type="match",
        target_id=match.id,
        data={k: result[k] for k in ("provider", "game_id", "created", "matched_video_goals")},
    )
    return result


async def apply(ctx: Ctx, match: Match, report: OfficialReport) -> dict[str, Any]:
    known = await _known(ctx, match)
    clock_map = match_clock.build(match, await _analysis(ctx, match), [])
    roster = await roster_numbers(ctx, match.season_id, match.team_id)
    added = _add_entries(ctx, match, report, known, clock_map, roster)
    unmatched_video = await _settle_video_goals(ctx, match, known, added)
    return await _write_result(ctx, match, report, known, added, unmatched_video)


async def import_report(
    ctx: Ctx, match_id: uuid.UUID, source: str, provider: str | None = None
) -> dict[str, Any]:
    """Checks the rights before anything is fetched."""
    match = await get_match(ctx, match_id, Action.EVENT_WRITE)
    report = await fetch(source, provider)
    if await org_verification.is_unverified(ctx, match.organization_id):
        report = without_opponent_names(report, match.is_home)
    return await apply(ctx, match, report)

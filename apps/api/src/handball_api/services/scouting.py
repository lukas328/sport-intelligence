"""Automatic preparation report (addendum 01, 4.6).

Built from our earlier matches against the opponent (events and video analysis). Every statement
carries its sample size and up to three clip references; observations are phrased as observations,
not as orders. Missing data is named explicitly (P3). Opponent players appear by number only (4.9).
"""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from handball_api.core.db import disable_system_access, enable_system_access, set_tenant
from handball_api.core.errors import ProblemError
from handball_api.models import Event, Match, Opponent, ScoutingReport, Team, VideoAsset
from handball_api.models.enums import TeamRole
from handball_api.services import audit, scouting_pdf, training
from handball_api.services.context import Ctx
from handball_api.services.matches import duration_ms, get_match, in_video, timeline_videos
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action, can

LEAD = timedelta(hours=72)
MIN_SAMPLE = 5  # below this an observation is not made
SUSPENSION_S = 120
CLIPS = 3


def _ref(e: Event, videos: dict[uuid.UUID, uuid.UUID]) -> dict[str, Any]:
    return {
        "event_id": str(e.id),
        "match_id": str(e.match_id),
        "video_id": str(videos[e.match_id]) if e.match_id in videos else None,
        "t_ms": e.t_ms,
    }


def _clips(
    events: list[Event],
    videos: dict[uuid.UUID, uuid.UUID],
    lengths: dict[uuid.UUID, int | None] | None = None,
) -> list[dict[str, Any]]:
    """The last few events each match's video shows (an official goal before or after a clip of
    part of the game has no moment to jump to)."""
    lengths = lengths or {}
    with_video = [
        e for e in events if e.match_id in videos and in_video(e.t_ms, lengths.get(e.match_id))
    ]
    return [_ref(e, videos) for e in with_video[-CLIPS:]]


def _pct(a: int, b: int) -> float | None:
    return round(a / b, 3) if b else None


def _windows(events: list[Event], side: str) -> list[tuple[int, float, float]]:
    """(match index, from, to) in match-clock seconds while `side` was short-handed."""
    return [
        (hash(e.match_id), e.clock_s, e.clock_s + SUSPENSION_S)
        for e in events
        if e.type == "suspension_2min" and e.side == side and e.clock_s is not None
    ]


def _inside(e: Event, windows: list[tuple[int, float, float]]) -> bool:
    return e.clock_s is not None and any(
        m == hash(e.match_id) and a <= e.clock_s < b for m, a, b in windows
    )


def build_facts(
    opponent: Opponent,
    matches: list[Match],
    events: list[Event],
    videos: dict[uuid.UUID, uuid.UUID],
    lengths: dict[uuid.UUID, int | None] | None = None,
) -> dict[str, Any]:
    tagged = sorted({e.match_id for e in events})
    opp_shots = [e for e in events if e.type == "shot" and e.side == "opponent"]
    own_shots = [e for e in events if e.type == "shot" and e.side == "own"]
    opp_goals = [e for e in opp_shots if e.outcome == "goal"]
    missing: list[str] = []
    if not tagged:
        missing.append("events")
    if not videos:
        missing.append("video")
    missing.append("play_detection")  # opponent plays need automatic play detection (A3)

    record = {"won": 0, "drawn": 0, "lost": 0}
    for m in matches:
        if m.score_own is not None and m.score_opponent is not None:
            k = (
                "won"
                if m.score_own > m.score_opponent
                else "drawn"
                if m.score_own == m.score_opponent
                else "lost"
            )
            record[k] += 1

    glance: dict[str, Any] = {
        "matches": len(matches),
        "tagged_matches": len(tagged),
        "record": record,
        "goals_per_match": round(len(opp_goals) / len(tagged), 1) if tagged else None,
        "shooting_pct": _pct(len(opp_goals), len(opp_shots)),
        "n": len(opp_shots),
    }

    by_number: dict[int, list[Event]] = defaultdict(list)
    for e in opp_shots:
        if e.number is not None:
            by_number[int(e.number)].append(e)
    shooters: list[dict[str, Any]] = []
    for number, shots in sorted(
        by_number.items(), key=lambda kv: -sum(1 for e in kv[1] if e.outcome == "goal")
    ):
        goals = [e for e in shots if e.outcome == "goal"]
        zones = Counter(e.shot_zone for e in shots if e.shot_zone)
        goal_zones = Counter(e.goal_zone for e in goals if e.goal_zone)
        shooters.append(
            {
                "number": number,
                "goals": len(goals),
                "shots": len(shots),
                "shooting_pct": _pct(len(goals), len(shots)),
                "zones": dict(zones.most_common()),
                "goal_zones": dict(goal_zones.most_common()),
                "main_zone": zones.most_common(1)[0][0] if zones else None,
                "n": len(shots),
                "clips": _clips(goals, videos, lengths),
            }
        )
    shooters = shooters[:6]

    fast = [e for e in opp_goals if e.shot_type == "fast_break" or e.shot_zone == "fast_break"]
    fast_break: dict[str, Any] = {
        "goals": len(fast),
        "share": _pct(len(fast), len(opp_goals)),
        "n": len(opp_goals),
        "clips": _clips(fast, videos, lengths),
    }

    our_short = _windows(events, "own")
    their_short = _windows(events, "opponent")
    pp_goals = [e for e in opp_goals if _inside(e, our_short)]
    our_goals = [e for e in own_shots if e.outcome == "goal"]
    sh_goals = [e for e in our_goals if _inside(e, their_short)]
    numbers: dict[str, dict[str, Any]] = {
        "they_in_powerplay": {
            "periods": len(our_short),
            "goals": len(pp_goals),
            "per_period": round(len(pp_goals) / len(our_short), 2) if our_short else None,
            "n": len(our_short),
            "clips": _clips(pp_goals, videos, lengths),
        },
        "we_in_powerplay": {
            "periods": len(their_short),
            "goals": len(sh_goals),
            "per_period": round(len(sh_goals) / len(their_short), 2) if their_short else None,
            "n": len(their_short),
            "clips": _clips(sh_goals, videos, lengths),
        },
    }

    # where we scored well against them: their defensive weak spots (our shots by zone)
    zone_stats: dict[str, list[Event]] = defaultdict(list)
    for e in own_shots:
        if e.shot_zone:
            zone_stats[e.shot_zone].append(e)
    weak: list[dict[str, Any]] = []
    for zone, shots in zone_stats.items():
        goals = [e for e in shots if e.outcome == "goal"]
        weak.append(
            {
                "zone": zone,
                "goals": len(goals),
                "shots": len(shots),
                "pct": _pct(len(goals), len(shots)),
                "n": len(shots),
                "clips": _clips(goals, videos, lengths),
            }
        )
    weak = sorted((w for w in weak if w["n"] >= 3), key=lambda w: -(w["pct"] or 0))[:3]
    defense: dict[str, Any] = {"weak_zones": weak, "formations_ms": {}}

    observations: list[dict[str, Any]] = []
    if shooters and glance["n"] >= MIN_SAMPLE and shooters[0]["goals"]:
        top = shooters[0]
        observations.append(
            {
                "key": "top_shooter",
                "params": {
                    "number": top["number"],
                    "goals": top["goals"],
                    "share": _pct(top["goals"], len(opp_goals)),
                    "zone": top["main_zone"],
                },
                "n": len(opp_goals),
                "clips": top["clips"],
            }
        )
    if fast_break["n"] >= MIN_SAMPLE and (fast_break["share"] or 0) >= 0.2:
        observations.append(
            {
                "key": "fast_break",
                "params": {"share": fast_break["share"], "goals": fast_break["goals"]},
                "n": fast_break["n"],
                "clips": fast_break["clips"],
            }
        )
    pp = numbers["they_in_powerplay"]
    if pp["n"] >= 3 and pp["per_period"] is not None and pp["per_period"] >= 1:
        observations.append(
            {
                "key": "powerplay",
                "params": {"per_period": pp["per_period"], "periods": pp["periods"]},
                "n": pp["n"],
                "clips": pp["clips"],
            }
        )
    for w in weak[:1]:
        if w["n"] >= MIN_SAMPLE and (w["pct"] or 0) >= 0.6:
            observations.append(
                {
                    "key": "weak_zone",
                    "params": {"zone": w["zone"], "pct": w["pct"], "shots": w["shots"]},
                    "n": w["n"],
                    "clips": w["clips"],
                }
            )

    return {
        "opponent": {"id": str(opponent.id), "name": opponent.name},
        "glance": glance,
        "shooters": shooters,
        "plays": {"available": False, "reason": "play_detection"},
        "defense": defense,
        "fast_break": fast_break,
        "numbers": numbers,
        "observations": observations,
        "missing": missing,
    }


async def _data(
    ctx: Ctx, team: Team, opponent: Opponent, before: datetime
) -> tuple[list[Match], list[Event], dict[uuid.UUID, uuid.UUID], dict[uuid.UUID, int | None]]:
    matches = list(
        (
            await ctx.db.scalars(
                select(Match)
                .where(
                    Match.team_id == team.id,
                    Match.opponent_id == opponent.id,
                    Match.kind == "match",
                    Match.kickoff_at < before,
                )
                .order_by(Match.kickoff_at)
            )
        ).all()
    )
    ids = [m.id for m in matches]
    events = list(
        (
            await ctx.db.scalars(
                select(Event).where(Event.match_id.in_(ids)).order_by(Event.match_id, Event.clock_s)
            )
        ).all()
    )
    timeline = await timeline_videos(ctx, ids)
    videos = {mid: v.id for mid, v in timeline.items()}
    lengths = {mid: duration_ms(v) for mid, v in timeline.items()}
    return matches, events, videos, lengths


async def create(ctx: Ctx, match: Match) -> ScoutingReport:
    if match.opponent_id is None:
        raise ProblemError(422, "no-opponent", "Trainings have no opponent")
    team = await ctx.db.get(Team, match.team_id)
    opponent = await ctx.db.get(Opponent, match.opponent_id)
    assert team is not None and opponent is not None
    matches, events, videos, lengths = await _data(ctx, team, opponent, match.kickoff_at)
    facts = build_facts(opponent, matches, events, videos, lengths)
    formations: Counter[str] = Counter()
    for v in (
        await ctx.db.scalars(select(VideoAsset).where(VideoAsset.id.in_(list(videos.values()))))
    ).all():
        for seg in (v.analysis or {}).get("formations") or []:
            if seg.get("team") == "away":
                formations[str(seg["formation"])] += int(seg["end_ms"]) - int(seg["start_ms"])
    facts["defense"]["formations_ms"] = dict(formations.most_common())
    report = ScoutingReport(
        organization_id=match.organization_id,
        team_id=team.id,
        match_id=match.id,
        opponent_id=opponent.id,
        generated_at=datetime.now(UTC),
        facts=facts,
        basis={
            "matches": len(matches),
            "tagged_matches": facts["glance"]["tagged_matches"],
            "events": len(events),
            "videos": len(videos),
        },
    )
    ctx.db.add(report)
    await ctx.db.flush()
    return report


async def generate(ctx: Ctx, match_id: uuid.UUID) -> ScoutingReport:
    match = await get_match(ctx, match_id, Action.CLIP_WRITE)
    report = await create(ctx, match)
    await audit.record(ctx, "scouting.generated", target_type="match", target_id=match.id)
    return report


async def latest(ctx: Ctx, match_id: uuid.UUID) -> ScoutingReport:
    match = await get_match(ctx, match_id)
    await get_team(ctx, match.team_id, Action.PLAYLIST_READ_ALL)
    report = await ctx.db.scalar(
        select(ScoutingReport)
        .where(ScoutingReport.match_id == match.id)
        .order_by(ScoutingReport.generated_at.desc())
        .limit(1)
    )
    if report is None:
        raise ProblemError(404, "not-found", "No preparation report yet")
    return report


async def run_due(ctx: Ctx, now: datetime | None = None) -> int:
    """Worker tick: reports for matches starting within 72 h that have none yet and for which
    data about the opponent exists. Notifies the team staff."""
    now = now or datetime.now(UTC)
    await enable_system_access(ctx.db, reason="scheduled preparation reports")
    try:
        done = select(ScoutingReport.match_id).where(ScoutingReport.match_id.is_not(None))
        due = list(
            (
                await ctx.db.scalars(
                    select(Match).where(
                        Match.kind == "match",
                        Match.kickoff_at > now,
                        Match.kickoff_at <= now + LEAD,
                        Match.id.not_in(done),
                    )
                )
            ).all()
        )
    finally:
        await disable_system_access(ctx.db)
    created = 0
    for m in due:
        await set_tenant(ctx.db, m.organization_id)
        earlier = await ctx.db.scalar(
            select(Match.id)
            .where(
                Match.team_id == m.team_id,
                Match.opponent_id == m.opponent_id,
                Match.kickoff_at < m.kickoff_at,
                Match.id.in_(select(Event.match_id)),
            )
            .limit(1)
        )
        if earlier is None:
            continue  # no data about this opponent: no report (the coach can still create one)
        await create(ctx, m)
        await training.notify(
            ctx,
            m.organization_id,
            await training.staff_of(ctx, m.team_id),
            "scouting_ready",
            {"match_id": str(m.id)},
            f"/app/{m.organization_id}/matches/{m.id}/scouting",
        )
        created += 1
    await ctx.db.flush()
    return created


async def pdf(ctx: Ctx, report_id: uuid.UUID, lang: str, card: bool) -> tuple[bytes, str]:
    """Report PDF for staff; the A6 shooter card also for the team's goalkeepers."""
    report = await ctx.db.get(ScoutingReport, report_id)
    if report is None:
        raise ProblemError(404, "not-found", "Report not found")
    team = await get_team(ctx, report.team_id)
    actor = ctx.require_actor()
    staff = can(actor, Action.PLAYLIST_READ_ALL, team.id)
    keeper = actor.team_role(team.id) in (TeamRole.GOALKEEPER, TeamRole.GOALKEEPER_COACH)
    if not (staff or (card and keeper)):
        raise ProblemError(403, "forbidden", "Only staff and goalkeepers")
    if card:
        return scouting_pdf.render_goalkeeper_card(lang, report.facts), "werferkarte.pdf"
    match = await ctx.db.get(Match, report.match_id) if report.match_id else None
    kickoff = match.kickoff_at if match else report.generated_at
    data = scouting_pdf.render_report(lang, team.name, kickoff, report.facts, report.basis)
    return data, "vorbereitung.pdf"

"""Opponents and matches."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, func, select

from handball_api.core.colors import kit_warnings
from handball_api.core.errors import ProblemError
from handball_api.models import (
    Event,
    Match,
    MatchSegment,
    Opponent,
    OpponentPlayer,
    Organization,
    ProcessingJob,
    Season,
    VideoAsset,
)
from handball_api.models.enums import MatchFormatKey, VideoRole, VideoStatus
from handball_api.schemas.matches import (
    JobOut,
    MatchCreate,
    MatchOut,
    MatchSummary,
    MatchUpdate,
    OpponentColors,
    OpponentCreate,
    OpponentOut,
    OpponentPlayerIn,
    OpponentUpdate,
    SyncOut,
    VideoOut,
)
from handball_api.services import audit, billing, match_formats
from handball_api.services.context import Ctx
from handball_api.services.orgs import current_seasons, get_team
from handball_api.services.policies import Action, authorize, is_staff_somewhere, visible_team_ids

# where events come from when a match report brought them (handball.ch, a paper report)
REPORT_SOURCES = ("official_feed", "paper_report", "official_report")


DUPLICATE = "same-file:"  # error of a file that is already in the match: "same-file:<video id>"


def duplicate_of(v: VideoAsset) -> uuid.UUID | None:
    if v.error and v.error.startswith(DUPLICATE):
        try:
            return uuid.UUID(v.error[len(DUPLICATE) :])
        except ValueError:
            return None
    return None


def video_out(v: VideoAsset, part: Part | None = None, half: int | None = None) -> VideoOut:
    return VideoOut(
        part=part.position + 1 if part is not None else None,
        half=half,
        part_start_ms=part.offset_ms if part is not None else None,
        duplicate_of=duplicate_of(v),
        id=v.id,
        role=v.role,
        status=v.status,
        filename=v.filename,
        size_bytes=v.size_bytes,
        duration_s=v.duration_s,
        fps=v.fps,
        width=v.width,
        height=v.height,
        codec=v.codec,
        has_hls=v.hls_prefix is not None,
        has_poster=v.poster_key is not None,
        has_thumbnails=bool(v.quality_report and v.quality_report.get("thumbnails")),
        time_offset_ms=v.time_offset_ms,
        sync=SyncOut.model_validate(
            {k: v.sync.get(k) for k in ("offset_ms", "confidence", "source", "applied")}
        )
        if v.sync and v.sync.get("source")
        else None,
        quality_report=v.quality_report,
        error=v.error,
        created_at=v.created_at,
    )


# ---- opponents -----------------------------------------------------------------------------


def _require_staff(ctx: Ctx) -> None:
    if not is_staff_somewhere(ctx.require_actor()):
        raise ProblemError(
            403, "forbidden", "Only coaches, analysts, team managers and admins manage opponents"
        )


async def list_opponents(ctx: Ctx) -> list[Opponent]:
    if visible_team_ids(ctx.require_actor()) == set():
        raise ProblemError(403, "forbidden", "No team access")
    return list((await ctx.db.scalars(select(Opponent).order_by(Opponent.name))).all())


async def _opponent(ctx: Ctx, opponent_id: uuid.UUID) -> Opponent:
    opp = await ctx.db.get(Opponent, opponent_id)
    if opp is None or opp.organization_id != ctx.require_actor().organization_id:
        raise ProblemError(404, "not-found", "Opponent not found")
    return opp


async def opponent_players(ctx: Ctx, opponent_id: uuid.UUID) -> list[OpponentPlayer]:
    if visible_team_ids(ctx.require_actor()) == set():
        raise ProblemError(403, "forbidden", "No team access")
    opp = await _opponent(ctx, opponent_id)
    rows = await ctx.db.scalars(
        select(OpponentPlayer)
        .where(OpponentPlayer.opponent_id == opp.id)
        .order_by(OpponentPlayer.number)
    )
    return list(rows.all())


async def put_opponent_players(
    ctx: Ctx, opponent_id: uuid.UUID, players: list[OpponentPlayerIn]
) -> list[OpponentPlayer]:
    """Replaces the opponent's list (numbers unique)."""
    _require_staff(ctx)
    opp = await _opponent(ctx, opponent_id)
    numbers = [p.number for p in players]
    if len(numbers) != len(set(numbers)):
        raise ProblemError(422, "duplicate-number", "Each number only once")
    await ctx.db.execute(delete(OpponentPlayer).where(OpponentPlayer.opponent_id == opp.id))
    for p in players:
        ctx.db.add(
            OpponentPlayer(
                organization_id=opp.organization_id,
                opponent_id=opp.id,
                entered_by_id=ctx.user_id,
                **p.model_dump(),
            )
        )
    await ctx.db.flush()
    await audit.record(
        ctx,
        "opponent.players_updated",
        target_type="opponent",
        target_id=opp.id,
        data={"count": len(players), "named": sum(1 for p in players if p.name)},
    )
    return await opponent_players(ctx, opp.id)


async def create_opponent(ctx: Ctx, data: OpponentCreate) -> Opponent:
    _require_staff(ctx)
    existing = await ctx.db.scalar(
        select(Opponent).where(func.lower(Opponent.name) == data.name.lower())
    )
    if existing:
        return existing
    opp = Opponent(organization_id=ctx.require_actor().organization_id, **data.model_dump())
    ctx.db.add(opp)
    await ctx.db.flush()
    return opp


async def update_opponent(ctx: Ctx, opponent_id: uuid.UUID, data: OpponentUpdate) -> Opponent:
    _require_staff(ctx)
    opp = await ctx.db.get(Opponent, opponent_id)
    if opp is None:
        raise ProblemError(404, "not-found", "Opponent not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(opp, k, v)
    return opp


# ---- matches -------------------------------------------------------------------------------


async def create_match(ctx: Ctx, team_id: uuid.UUID, data: MatchCreate) -> Match:
    team = await get_team(ctx, team_id, Action.MATCH_WRITE)
    if data.season_id:
        season = await ctx.db.get(Season, data.season_id)
        if season is None or season.team_id != team.id:
            raise ProblemError(404, "not-found", "Season not found")
    else:
        season = (await current_seasons(ctx, [team.id])).get(team.id)
        if season is None:
            raise ProblemError(409, "no-season", "The team has no season")
    await billing.check_new_match(ctx, team.organization_id, team.id, season.id)
    opp: Opponent | None = None
    if data.opponent_id:
        opp = await ctx.db.get(Opponent, data.opponent_id)
        if opp is None:
            raise ProblemError(404, "not-found", "Opponent not found")
    elif data.opponent_name:
        opp = await create_opponent(ctx, OpponentCreate(name=data.opponent_name))
    values = data.model_dump(
        exclude={"season_id", "opponent_id", "opponent_name", "format", "period_s", "periods"}
    )
    # the opponent's colour: said now (opponent_kit or an explicit kit_opponent), or remembered
    said = data.opponent_kit or (
        data.kit_opponent if "kit_opponent" in data.model_fields_set else None
    )
    values["opponent_kit"] = said if opp else None
    # our own shirts: the club's colour unless the form said another (real-video test E09)
    if "kit_own" not in data.model_fields_set:
        org = await ctx.db.get(Organization, team.organization_id)
        if org is not None and org.primary_color:
            values["kit_own"] = org.primary_color
    if opp and said:
        opp.primary_color = said
    elif opp and opp.primary_color and "kit_opponent" not in data.model_fields_set:
        # the pipeline gets the remembered colour instead of the default
        values["kit_opponent"] = opp.primary_color
    default = (
        MatchFormatKey(team.default_format)
        if team.default_format
        else match_formats.default_for(team.is_youth)
    )
    values["format"], values["period_s"], values["periods"] = _format(
        data.format or default, data.period_s, data.periods
    )
    match = Match(
        organization_id=team.organization_id,
        team_id=team.id,
        season_id=season.id,
        opponent_id=opp.id if opp else None,
        **values,
    )
    ctx.db.add(match)
    await ctx.db.flush()
    await audit.record(ctx, "match.created", target_type="match", target_id=match.id)
    return match


async def list_matches(
    ctx: Ctx, team_id: uuid.UUID, season_id: uuid.UUID | None = None
) -> list[MatchSummary]:
    await get_team(ctx, team_id, Action.MATCH_READ)
    # a report is there once its events are (UX test A02: «Spielbericht hinzufügen» only without)
    report = (
        select(Event.id)
        .where(Event.match_id == Match.id, Event.source.in_(REPORT_SOURCES))
        .exists()
        .correlate(Match)
    )
    q = (
        select(Match, Opponent.name, Opponent.primary_color, func.count(VideoAsset.id), report)
        .outerjoin(Opponent, Opponent.id == Match.opponent_id)
        .outerjoin(VideoAsset, VideoAsset.match_id == Match.id)
        .where(Match.team_id == team_id)
        .group_by(Match.id, Opponent.name, Opponent.primary_color)
        .order_by(Match.kickoff_at.desc())
    )
    if season_id:
        q = q.where(Match.season_id == season_id)
    rows = (await ctx.db.execute(q)).all()
    return [
        MatchSummary(
            id=m.id,
            team_id=m.team_id,
            kind=m.kind,
            opponent_name=name or "",
            kickoff_at=m.kickoff_at,
            is_home=m.is_home,
            competition=m.competition,
            score_own=m.score_own,
            score_opponent=m.score_opponent,
            status=m.status,
            is_demo=m.is_demo,
            has_video=count > 0,
            opponent_color=m.opponent_kit or remembered,
            has_report=bool(has_report),
        )
        for m, name, remembered, count, has_report in rows
    ]


async def get_match(ctx: Ctx, match_id: uuid.UUID, action: Action = Action.MATCH_READ) -> Match:
    match = await ctx.db.get(Match, match_id)
    actor = ctx.require_actor()
    if match is None:
        raise ProblemError(404, "not-found", "Match not found")
    visible = visible_team_ids(actor)
    if visible is not None and match.team_id not in visible:
        raise ProblemError(404, "not-found", "Match not found")
    authorize(actor, action, match.team_id, two_factor=ctx.two_factor)
    return match


# ---- the match timeline -----------------------------------------------------------------------
# Event and clip times (t_ms) are times on the match timeline: the main files of the match (its
# parts: two halves, a recording the phone split) one after the other, in the order of their
# MatchSegment rows (camera clock, else upload order, or as a person swapped them). Part k starts
# at the sum of the lengths of the parts before it. A match with one file has the file's own times.
# Tracks, the court and the defence formations stay per file (times in that file); `locate` maps a
# timeline time to the file and its time. Events aligned from the match clock or an official report
# can lie before the video (clip starts mid-half: negative times) or after its end.
# The first part is the timeline video: its player playlist joins all parts (services/timeline).


@dataclass(frozen=True)
class Part:
    """One file of the match timeline. `offset_ms` is None while a part before it has no known
    length (its times cannot be placed yet)."""

    video_id: uuid.UUID
    position: int
    offset_ms: int | None
    duration_ms: int | None
    status: VideoStatus
    filename: str
    gap_before_ms: int | None = None
    side_change: bool | None = None  # said by the coach; None: from the gap

    @property
    def end_ms(self) -> int | None:
        if self.offset_ms is None or self.duration_ms is None:
            return None
        return self.offset_ms + self.duration_ms


def _timeline_query(match_ids: list[uuid.UUID]) -> Any:
    """Main files that are not failed, the parts in their order first, then files without a
    MatchSegment yet (still processing) in upload order."""
    return (
        select(VideoAsset)
        .outerjoin(MatchSegment, MatchSegment.video_id == VideoAsset.id)
        .where(
            VideoAsset.match_id.in_(match_ids),
            VideoAsset.role == VideoRole.MAIN,
            VideoAsset.status != VideoStatus.FAILED,
        )
        .order_by(
            VideoAsset.match_id,
            MatchSegment.position.is_(None),
            MatchSegment.position,
            VideoAsset.created_at,
            VideoAsset.id,
        )
    )


async def parts_of(ctx: Ctx, match_id: uuid.UUID) -> list[Part]:
    """The parts of the match timeline in order, with their place on it."""
    rows = (
        await ctx.db.execute(
            select(MatchSegment, VideoAsset)
            .join(VideoAsset, VideoAsset.id == MatchSegment.video_id)
            .where(
                MatchSegment.match_id == match_id,
                VideoAsset.role == VideoRole.MAIN,
                VideoAsset.status != VideoStatus.FAILED,
            )
            .order_by(MatchSegment.position, VideoAsset.created_at)
        )
    ).all()
    out: list[Part] = []
    offset: int | None = 0
    for i, (seg, v) in enumerate(rows):
        length = duration_ms(v)
        out.append(
            Part(
                v.id,
                i,
                offset,
                length,
                v.status,
                v.filename,
                seg.gap_before_ms if i else None,
                seg.side_change if i else None,
            )
        )
        offset = None if offset is None or length is None else offset + length
    return out


# a part after a break of at least this long is the next half (the half-time break is 10 to 15
# minutes); after a gap shorter than NO_BREAK_MS the recording only went on (the phone split it,
# the coach restarted it): no side change (Echtlauf 5 P9)
HALF_BREAK_MS = 5 * 60_000
NO_BREAK_MS = 60_000
# a part this short is a recording started by mistake, not a half
MIN_HALF_MS = 60_000


def stray(parts: list[Part], part: Part) -> bool:
    """A few seconds started by mistake: under a minute, next to a part at least four times as
    long (two short clips, as in tests, are not a mistake; the web says it the same way,
    lib/video-parts.ts isShort)."""
    if part.duration_ms is None or part.duration_ms >= MIN_HALF_MS:
        return False
    others = [p for p in parts if p.video_id != part.video_id]
    if any(p.duration_ms is None for p in others):
        return True
    return max((int(p.duration_ms or 0) for p in others), default=0) >= 4 * part.duration_ms


def real_parts(parts: list[Part]) -> list[Part]:
    """The parts that can be halves (not a few seconds started by mistake)."""
    return [p for p in parts if not stray(parts, p)]


def second_half(parts: list[Part], part: Part) -> bool:
    """A part after which the teams play on the other ends: what the coach said, else the second
    of two parts unless the recordings follow each other within a minute, or a part after a break
    as long as a half-time break."""
    if part.position == 0 or stray(parts, part):
        return False
    if part.side_change is not None:
        return part.side_change
    if part.gap_before_ms is not None and part.gap_before_ms < NO_BREAK_MS:
        return False
    real = real_parts(parts)
    if len(real) == 2 and real[1].video_id == part.video_id:
        return True
    return part.gap_before_ms is not None and part.gap_before_ms >= HALF_BREAK_MS


def halves(parts: list[Part]) -> dict[uuid.UUID, int]:
    """The half of each part when the match is two halves (two real parts with a side change
    between them): named «1. / 2. Halbzeit»; otherwise none («Teil 1 / Teil 2»). A short part
    started by mistake does not count."""
    real = real_parts(parts)
    if len(real) != 2 or not second_half(parts, real[1]):
        return {}
    return {real[0].video_id: 1, real[1].video_id: 2}


def locate(parts: list[Part], t_ms: int) -> tuple[Part, int] | None:
    """The part a timeline time lies in and the time in that file. Times before the first part
    belong to it, times after the last part to the last one (as negative times always did)."""
    placed = [p for p in parts if p.offset_ms is not None]
    if not placed:
        return None
    hit = placed[0]
    for p in placed:
        if t_ms >= int(p.offset_ms or 0):
            hit = p
    return hit, t_ms - int(hit.offset_ms or 0)


def timeline_length_ms(parts: list[Part]) -> int | None:
    """Length of the whole timeline, None while a part's length is unknown."""
    if not parts:
        return None
    return parts[-1].end_ms


async def timeline_video(ctx: Ctx, match_id: uuid.UUID, ready: bool = False) -> VideoAsset | None:
    """The first part of the match timeline (its player plays all parts); with `ready`, only once
    it plays."""
    v: VideoAsset | None = await ctx.db.scalar(_timeline_query([match_id]).limit(1))
    if v is not None and ready and v.status != VideoStatus.READY:
        return None
    return v


@dataclass(frozen=True)
class TimelineVideo:
    """What callers of timeline_videos need of a match's timeline video (not its analysis);
    `duration_s` is the length of the whole timeline (all parts)."""

    id: uuid.UUID
    match_id: uuid.UUID
    status: VideoStatus
    duration_s: float | None


async def timeline_videos(
    ctx: Ctx, match_ids: list[uuid.UUID] | set[uuid.UUID], ready: bool = True
) -> dict[uuid.UUID, TimelineVideo]:
    """timeline_video for several matches in one query, only the columns callers use (the
    analysis JSON of a full game is large: video_formations reads the part that is needed)."""
    if not match_ids:
        return {}
    first: dict[uuid.UUID, TimelineVideo] = {}
    total: dict[uuid.UUID, float | None] = {}
    rows = await ctx.db.execute(
        _timeline_query(list(match_ids)).with_only_columns(
            VideoAsset.id,
            VideoAsset.match_id,
            VideoAsset.status,
            VideoAsset.duration_s,
            MatchSegment.id,
        )
    )
    for vid, match_id, status, duration_s, seg in rows.all():
        if match_id not in first:
            first[match_id] = TimelineVideo(vid, match_id, status, duration_s)
            total[match_id] = duration_s
        elif seg is not None:  # a further part on the timeline
            sofar = total[match_id]
            total[match_id] = None if sofar is None or duration_s is None else sofar + duration_s
    return {
        m: TimelineVideo(v.id, m, v.status, total[m])
        for m, v in first.items()
        if not ready or v.status == VideoStatus.READY
    }


async def video_formations(
    ctx: Ctx, video_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[dict[str, Any]]]:
    """The defence formations the analysis found per video (only that part of the analysis);
    for a timeline video, those of every part of its match, on the match timeline."""
    if not video_ids:
        return {}
    rows = await ctx.db.execute(
        select(VideoAsset.id, VideoAsset.match_id, VideoAsset.analysis["formations"]).where(
            VideoAsset.id.in_(video_ids)
        )
    )
    out: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for vid, match_id, f in rows.all():
        parts = await parts_of(ctx, match_id)
        if len(parts) < 2 or parts[0].video_id != vid:
            out[vid] = list(f) if isinstance(f, list) else []
            continue
        out[vid] = await _formations_on_timeline(ctx, parts)
    return out


async def _formations_on_timeline(ctx: Ctx, parts: list[Part]) -> list[dict[str, Any]]:
    placed = {p.video_id: int(p.offset_ms) for p in parts if p.offset_ms is not None}
    rows = await ctx.db.execute(
        select(VideoAsset.id, VideoAsset.analysis["formations"]).where(
            VideoAsset.id.in_(list(placed))
        )
    )
    out: list[dict[str, Any]] = []
    for vid, f in rows.all():
        for item in f if isinstance(f, list) else []:
            if not isinstance(item, dict):
                continue
            shifted = dict(item)
            for k in ("start_ms", "end_ms", "t_ms"):
                if isinstance(shifted.get(k), int | float):
                    shifted[k] = int(shifted[k]) + placed[vid]
            out.append(shifted)
    return sorted(out, key=lambda x: int(x.get("start_ms", x.get("t_ms", 0)) or 0))


def duration_ms(video: VideoAsset | TimelineVideo | None) -> int | None:
    return round(video.duration_s * 1000) if video is not None and video.duration_s else None


async def video_duration_ms(ctx: Ctx, match: Match) -> int | None:
    """Length of the match timeline (all parts), None while unknown."""
    parts = await parts_of(ctx, match.id)
    if parts:
        return timeline_length_ms(parts)
    return duration_ms(await timeline_video(ctx, match.id))


async def timeline_duration_ms(ctx: Ctx, match_id: uuid.UUID) -> int | None:
    """video_duration_ms by match id."""
    parts = await parts_of(ctx, match_id)
    if parts:
        return timeline_length_ms(parts)
    return duration_ms(await timeline_video(ctx, match_id))


def in_video(t_ms: int | None, duration: int | None) -> bool:
    """The time lies inside the video (unknown length: any time from 0)."""
    if t_ms is None or t_ms < 0:
        return False
    return duration is None or t_ms <= duration


# The scene of an event, one rule for Szenen, Sammlung, Zusammenschnitt, the player's feed, the
# tactics camera and the Video tab (real-clip test of «Von wo?», V6): 6 s before to 3 s after; a
# goal confirmed from a goal candidate from 12 s before its time to 5 s after, because candidate
# times mostly lie 4 to 7 s after the goal but sometimes a few seconds before it (Q-REC-CANDTIME;
# seventh real-video test: a fast break scored 3 s after its candidate). Report goals and goals
# marked by hand keep 6 s and 3 s.
SCENE_PRE_MS, SCENE_POST_MS = 6_000, 3_000
CANDIDATE_PRE_MS, CANDIDATE_POST_MS = 12_000, 5_000


def from_candidate(e: Any) -> bool:
    """The event's video time is a goal candidate's (confirmed in Prüfen, or a report entry pinned
    to a candidate)."""
    if getattr(e, "source", None) == "goal_candidate":
        return True
    video = (getattr(e, "attributes", None) or {}).get("video")
    return isinstance(video, dict) and video.get("source") == "goal_candidate"


def scene_lead(e: Any, usual: tuple[int, int] = (SCENE_PRE_MS, SCENE_POST_MS)) -> tuple[int, int]:
    """How long the scene of `e` runs before and after its time (see SCENE_PRE_MS); `usual` for
    a view with its own lead for other events (the tactics camera: 8 s and 2 s)."""
    if from_candidate(e):
        return CANDIDATE_PRE_MS, CANDIDATE_POST_MS
    return usual


def scene_window(e: Any, duration: int | None) -> tuple[int, int]:
    """The scene of an event with a video time, cut at the video's start and end."""
    pre, post = scene_lead(e)
    return clip_window(int(e.t_ms), pre, post, duration)


def clip_window(t_ms: int, pre_ms: int, post_ms: int, duration: int | None) -> tuple[int, int]:
    """Clip around a time inside the video, cut at its start and end."""
    end = t_ms + post_ms if duration is None else min(duration, t_ms + post_ms)
    return max(0, t_ms - pre_ms), max(end, t_ms + 1)


async def opponent_of(ctx: Ctx, match: Match) -> Opponent | None:
    return await ctx.db.get(Opponent, match.opponent_id) if match.opponent_id else None


async def match_out(ctx: Ctx, match: Match) -> MatchOut:
    opp = await opponent_of(ctx, match)
    layout = await parts_of(ctx, match.id)
    parts = {p.video_id: p for p in layout}
    half = halves(layout)
    videos = sorted(
        (
            await ctx.db.scalars(
                select(VideoAsset)
                .where(VideoAsset.match_id == match.id)
                .order_by(VideoAsset.created_at)
            )
        ).all(),
        # the parts in their order first: the first ready main file is the first part
        key=lambda v: (v.id not in parts, parts[v.id].position if v.id in parts else 0),
    )
    jobs = (
        await ctx.db.scalars(
            select(ProcessingJob)
            .where(ProcessingJob.match_id == match.id)
            .order_by(ProcessingJob.created_at.desc())
            .limit(20)
        )
    ).all()
    return MatchOut(
        id=match.id,
        team_id=match.team_id,
        season_id=match.season_id,
        kind=match.kind,
        opponent=OpponentOut.model_validate(opp) if opp else None,
        kickoff_at=match.kickoff_at,
        is_home=match.is_home,
        competition=match.competition,
        venue=match.venue,
        kit_own=match.kit_own,
        kit_own_gk=match.kit_own_gk,
        kit_opponent=match.kit_opponent,
        kit_opponent_gk=match.kit_opponent_gk,
        kit_referee=match.kit_referee,
        opponent_colors=opponent_colors(match, opp) if opp else None,
        kit_warnings=kit_warnings(
            {
                "own": match.kit_own,
                "own_gk": match.kit_own_gk,
                "opponent": match.kit_opponent,
                "opponent_gk": match.kit_opponent_gk,
                **({"referee": match.kit_referee} if match.kit_referee else {}),
            }
        ),
        format=match.format,
        period_s=match.period_s,
        periods=match.periods,
        score_own=match.score_own,
        score_opponent=match.score_opponent,
        halftime_own=match.halftime_own,
        halftime_opponent=match.halftime_opponent,
        status=match.status,
        source=match.source,
        is_demo=match.is_demo,
        kickoff_ms=match.kickoff_ms,
        report_extra=match.report_extra,
        videos=[video_out(v, parts.get(v.id), half.get(v.id)) for v in videos],
        jobs=[JobOut.model_validate(j) for j in jobs],
    )


def opponent_colors(match: Match, opp: Opponent) -> OpponentColors:
    """Said for this match, else remembered for the opponent, else unknown (never guessed)."""
    if match.opponent_kit:
        return OpponentColors(color=match.opponent_kit, second=opp.secondary_color, source="match")
    if opp.primary_color:
        return OpponentColors(
            color=opp.primary_color, second=opp.secondary_color, source="opponent"
        )
    return OpponentColors(color=None, second=opp.secondary_color, source=None)


def _format(key: MatchFormatKey, period_s: int | None, periods: int | None) -> tuple[str, int, int]:
    try:
        return match_formats.resolve(key, period_s, periods)
    except ValueError as exc:
        raise ProblemError(422, "invalid-format", str(exc)) from exc


async def update_match(ctx: Ctx, match_id: uuid.UUID, data: MatchUpdate) -> Match:
    match = await get_match(ctx, match_id, Action.MATCH_WRITE)
    changes = data.model_dump(exclude_unset=True)
    fmt_keys = {"format", "period_s", "periods"}
    if fmt_keys & changes.keys():
        key = changes.get("format") or MatchFormatKey.CUSTOM
        keep = key == MatchFormatKey.CUSTOM  # custom keeps the current values unless given
        match.format, match.period_s, match.periods = _format(
            key,
            changes.get("period_s") or (match.period_s if keep else None),
            changes.get("periods") or (match.periods if keep else None),
        )
    if "opponent_kit" not in changes and changes.get("kit_opponent"):
        # a changed shirt colour is the opponent's colour in this match
        changes["opponent_kit"] = changes["kit_opponent"]
    for k, v in changes.items():
        if k not in fmt_keys:
            setattr(match, k, v)
    if changes.get("opponent_kit") and match.opponent_id:
        opp = await ctx.db.get(Opponent, match.opponent_id)
        if opp is not None:
            opp.primary_color = changes["opponent_kit"]
    await audit.record(
        ctx,
        "match.updated",
        target_type="match",
        target_id=match.id,
        data=data.model_dump(exclude_unset=True, mode="json"),
    )
    return match


async def delete_match(ctx: Ctx, match_id: uuid.UUID) -> None:
    """Deletes the match with all videos, derived files and data (BRIEF 12, deletion)."""
    match = await get_match(ctx, match_id, Action.MATCH_WRITE)
    videos = (await ctx.db.scalars(select(VideoAsset).where(VideoAsset.match_id == match.id))).all()
    for v in videos:
        if v.upload_id and v.status == "uploading":
            await ctx.storage.abort_multipart(
                ctx.settings.s3_bucket_videos, v.storage_key, v.upload_id
            )
    prefix = f"{match.organization_id}/{match.id}/"
    removed = 0
    for bucket in (ctx.settings.s3_bucket_videos, ctx.settings.s3_bucket_artifacts):
        removed += await ctx.storage.delete_prefix(bucket, prefix)
    await ctx.db.delete(match)
    await audit.record(
        ctx,
        "match.deleted",
        target_type="match",
        target_id=match_id,
        data={"objects_removed": removed, "videos": len(videos)},
    )

"""Opponents and matches."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from handball_api.core.errors import ProblemError
from handball_api.models import Match, Opponent, ProcessingJob, Season, VideoAsset
from handball_api.schemas.matches import (
    JobOut,
    MatchCreate,
    MatchOut,
    MatchSummary,
    MatchUpdate,
    OpponentCreate,
    OpponentOut,
    OpponentUpdate,
    VideoOut,
)
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.orgs import current_seasons, get_team
from handball_api.services.policies import Action, authorize, is_staff_somewhere, visible_team_ids


def video_out(v: VideoAsset) -> VideoOut:
    return VideoOut(
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
        quality_report=v.quality_report,
        error=v.error,
        created_at=v.created_at,
    )


# ---- opponents -----------------------------------------------------------------------------


def _require_staff(ctx: Ctx) -> None:
    if not is_staff_somewhere(ctx.require_actor()):
        raise ProblemError(403, "forbidden", "Only coaches, analysts and admins manage opponents")


async def list_opponents(ctx: Ctx) -> list[Opponent]:
    if visible_team_ids(ctx.require_actor()) == set():
        raise ProblemError(403, "forbidden", "No team access")
    return list((await ctx.db.scalars(select(Opponent).order_by(Opponent.name))).all())


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
    if data.opponent_id:
        opp = await ctx.db.get(Opponent, data.opponent_id)
        if opp is None:
            raise ProblemError(404, "not-found", "Opponent not found")
    else:
        assert data.opponent_name is not None
        opp = await create_opponent(ctx, OpponentCreate(name=data.opponent_name))
    values = data.model_dump(exclude={"season_id", "opponent_id", "opponent_name"})
    match = Match(
        organization_id=team.organization_id,
        team_id=team.id,
        season_id=season.id,
        opponent_id=opp.id,
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
    q = (
        select(Match, Opponent.name, func.count(VideoAsset.id))
        .join(Opponent, Opponent.id == Match.opponent_id)
        .outerjoin(VideoAsset, VideoAsset.match_id == Match.id)
        .where(Match.team_id == team_id)
        .group_by(Match.id, Opponent.name)
        .order_by(Match.kickoff_at.desc())
    )
    if season_id:
        q = q.where(Match.season_id == season_id)
    rows = (await ctx.db.execute(q)).all()
    return [
        MatchSummary(
            id=m.id,
            team_id=m.team_id,
            opponent_name=name,
            kickoff_at=m.kickoff_at,
            is_home=m.is_home,
            competition=m.competition,
            score_own=m.score_own,
            score_opponent=m.score_opponent,
            status=m.status,
            is_demo=m.is_demo,
            has_video=count > 0,
        )
        for m, name, count in rows
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


async def match_out(ctx: Ctx, match: Match) -> MatchOut:
    opp = await ctx.db.get(Opponent, match.opponent_id)
    assert opp is not None
    videos = (
        await ctx.db.scalars(
            select(VideoAsset)
            .where(VideoAsset.match_id == match.id)
            .order_by(VideoAsset.created_at)
        )
    ).all()
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
        opponent=OpponentOut.model_validate(opp),
        kickoff_at=match.kickoff_at,
        is_home=match.is_home,
        competition=match.competition,
        venue=match.venue,
        kit_own=match.kit_own,
        kit_own_gk=match.kit_own_gk,
        kit_opponent=match.kit_opponent,
        kit_opponent_gk=match.kit_opponent_gk,
        score_own=match.score_own,
        score_opponent=match.score_opponent,
        halftime_own=match.halftime_own,
        halftime_opponent=match.halftime_opponent,
        status=match.status,
        source=match.source,
        is_demo=match.is_demo,
        kickoff_ms=match.kickoff_ms,
        report_extra=match.report_extra,
        videos=[video_out(v) for v in videos],
        jobs=[JobOut.model_validate(j) for j in jobs],
    )


async def update_match(ctx: Ctx, match_id: uuid.UUID, data: MatchUpdate) -> Match:
    match = await get_match(ctx, match_id, Action.MATCH_WRITE)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(match, k, v)
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

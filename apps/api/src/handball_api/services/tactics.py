"""Play library and tactics board (M6)."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.models import Match, Play
from handball_api.schemas.tactics import PlayCreate, PlayUpdate
from handball_api.services import audit, billing
from handball_api.services.context import Ctx
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action, can


async def _play(ctx: Ctx, play_id: uuid.UUID, write: bool = False) -> Play:
    play = await ctx.db.get(Play, play_id)
    if play is None:
        raise ProblemError(404, "not-found", "Play not found")
    await get_team(ctx, play.team_id, Action.PLAY_WRITE if write else Action.TEAM_READ)
    if (
        not write
        and not play.shared_with_players
        and not can(ctx.require_actor(), Action.PLAY_READ_ALL, play.team_id)
    ):
        raise ProblemError(404, "not-found", "Play not found")
    return play


async def list_plays(
    ctx: Ctx, team_id: uuid.UUID, category: str | None = None, q: str | None = None
) -> list[Play]:
    await get_team(ctx, team_id, Action.TEAM_READ)
    stmt = select(Play).where(Play.team_id == team_id).order_by(Play.updated_at.desc())
    if not can(ctx.require_actor(), Action.PLAY_READ_ALL, team_id):
        stmt = stmt.where(Play.shared_with_players.is_(True))
    if category:
        stmt = stmt.where(Play.category == category)
    plays = list((await ctx.db.scalars(stmt)).all())
    if q:
        needle = q.strip().lower()
        plays = [
            p
            for p in plays
            if needle in p.name.lower()
            or needle in (p.formation or "").lower()
            or any(needle in t.lower() for t in p.tags)
        ]
    return plays


async def get_play(ctx: Ctx, play_id: uuid.UUID) -> Play:
    return await _play(ctx, play_id)


async def create_play(ctx: Ctx, team_id: uuid.UUID, data: PlayCreate) -> Play:
    team = await get_team(ctx, team_id, Action.PLAY_WRITE)
    await billing.require_feature(ctx, "tactics", team.organization_id)
    source = None
    if data.source is not None:
        match = await ctx.db.get(Match, data.source.match_id)
        if match is None or match.team_id != team.id:
            raise ProblemError(422, "validation", "The source match belongs to another team")
        source = {"match_id": str(match.id), "t_ms": data.source.t_ms}
    play = Play(
        organization_id=team.organization_id,
        team_id=team.id,
        name=data.name,
        category=data.category,
        formation=data.formation,
        description=data.description,
        tags=data.tags,
        doc=data.doc.model_dump(mode="json"),
        source=source,
        shared_with_players=data.shared_with_players,
        created_by_id=ctx.user_id,
    )
    ctx.db.add(play)
    await ctx.db.flush()
    await audit.record(ctx, "play.created", target_type="play", target_id=play.id)
    return play


async def update_play(ctx: Ctx, play_id: uuid.UUID, data: PlayUpdate) -> Play:
    play = await _play(ctx, play_id, write=True)
    values = data.model_dump(exclude_unset=True, mode="json")
    if "tags" in values and values["tags"] is not None:
        values["tags"] = sorted({t.strip()[:30] for t in values["tags"] if t.strip()})
    for k, v in values.items():
        if k in ("name", "category", "doc", "tags", "shared_with_players") and v is None:
            continue
        setattr(play, k, v)
    await ctx.db.flush()
    await ctx.db.refresh(play)
    return play


async def delete_play(ctx: Ctx, play_id: uuid.UUID) -> None:
    play = await _play(ctx, play_id, write=True)
    await ctx.db.delete(play)
    await audit.record(ctx, "play.deleted", target_type="play", target_id=play_id)

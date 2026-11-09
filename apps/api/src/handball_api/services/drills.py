"""Drill library (M7): the static drills of `packages/tactics` (kept as a copy in drills.json, a
vitest there checks it) and the club's own drills, listed in one shape.

Own drills belong to the team whose staff made them (`training.write`); shared drills are seen
by every team of the club, read-only for the other teams. Players read drills like the static
library (assignments send them to one); parents and guests see only the static library.
"""

from __future__ import annotations

import json
import uuid
from functools import cache
from pathlib import Path
from typing import Any

from sqlalchemy import or_, select

from handball_api.core.errors import ProblemError
from handball_api.models import ClubDrill, Team
from handball_api.models.enums import DrillLevel
from handball_api.schemas.drills import DrillIn, DrillOut
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action, can, visible_team_ids

LANGS = ("de-CH", "en", "fr")


@cache
def library() -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = json.loads(
        Path(__file__).with_name("drills.json").read_text("utf-8")
    )
    return data


def _text(value: dict[str, str], lang: str) -> str:
    return value.get(lang) or value["de-CH"]


def _library_out(d: dict[str, Any], lang: str) -> DrillOut:
    return DrillOut(
        id=d["id"],
        source="library",
        own=False,
        name=_text(d["name"], lang),
        setup=_text(d["setup"], lang),
        coaching=_text(d["coaching"], lang),
        minutes=d["minutes"],
        players=d["players"],
        level=d["level"],
        focus=list(d["focus"]),
        team_id=None,
        team_name=None,
        shared=True,
        editable=False,
        updated_at=None,
    )


def _club_out(ctx: Ctx, d: ClubDrill, team_name: str | None) -> DrillOut:
    return DrillOut(
        id=str(d.id),
        source="club",
        own=True,
        name=d.name,
        setup=d.setup,
        coaching=d.coaching,
        minutes=d.minutes,
        players=d.players,
        level=d.level.value if d.level else None,
        focus=list(d.focus),
        team_id=d.team_id,
        team_name=team_name,
        shared=d.shared,
        editable=can(ctx.require_actor(), Action.TRAINING_WRITE, d.team_id),
        updated_at=d.updated_at,
    )


async def list_drills(ctx: Ctx, team_id: uuid.UUID, lang: str) -> list[DrillOut]:
    """The team's own drills and the drills shared in the club (by name), then the library."""
    team = await get_team(ctx, team_id, Action.TEAM_READ)
    rows = (
        await ctx.db.execute(
            select(ClubDrill, Team.name)
            .join(Team, Team.id == ClubDrill.team_id)
            .where(
                ClubDrill.organization_id == team.organization_id,
                or_(ClubDrill.team_id == team.id, ClubDrill.shared.is_(True)),
            )
            .order_by(ClubDrill.name, ClubDrill.created_at)
        )
    ).all()
    own = [_club_out(ctx, d, name) for d, name in rows]
    return own + [_library_out(d, lang) for d in library()]


def _visible(ctx: Ctx, d: ClubDrill) -> bool:
    teams = visible_team_ids(ctx.require_actor())
    return teams is None or d.team_id in teams or (d.shared and bool(teams))


async def _drill(ctx: Ctx, drill_id: uuid.UUID) -> ClubDrill:
    d = await ctx.db.get(ClubDrill, drill_id)
    org = ctx.require_actor().organization_id
    if d is None or d.organization_id != org or not _visible(ctx, d):
        raise ProblemError(404, "not-found", "Drill not found")
    return d


async def _team_name(ctx: Ctx, team_id: uuid.UUID) -> str | None:
    team = await ctx.db.get(Team, team_id)
    return team.name if team else None


async def get_drill(ctx: Ctx, drill_id: str, lang: str) -> DrillOut:
    """A library drill by its key, or a club drill by its id."""
    ctx.require_actor()
    for d in library():
        if d["id"] == drill_id:
            return _library_out(d, lang)
    try:
        key = uuid.UUID(drill_id)
    except ValueError:
        raise ProblemError(404, "not-found", "Drill not found") from None
    drill = await _drill(ctx, key)
    return _club_out(ctx, drill, await _team_name(ctx, drill.team_id))


def _apply(d: ClubDrill, data: DrillIn) -> None:
    d.name = data.name
    d.setup = data.setup or None
    d.coaching = data.coaching or None
    d.minutes = data.minutes
    d.players = data.players
    d.level = DrillLevel(data.level) if data.level else None
    d.focus = list(dict.fromkeys(data.focus))
    d.shared = data.shared


async def create_drill(ctx: Ctx, team_id: uuid.UUID, data: DrillIn) -> DrillOut:
    team = await get_team(ctx, team_id, Action.TRAINING_WRITE)
    d = ClubDrill(
        organization_id=team.organization_id,
        team_id=team.id,
        created_by_id=ctx.require_actor().user_id,
    )
    _apply(d, data)
    ctx.db.add(d)
    await ctx.db.flush()
    await ctx.db.refresh(d)
    await audit.record(ctx, "drill.created", target_type="club_drill", target_id=d.id)
    return _club_out(ctx, d, team.name)


async def update_drill(ctx: Ctx, drill_id: uuid.UUID, data: DrillIn) -> DrillOut:
    d = await _drill(ctx, drill_id)
    team = await get_team(ctx, d.team_id, Action.TRAINING_WRITE)
    _apply(d, data)
    await ctx.db.flush()
    await ctx.db.refresh(d)
    return _club_out(ctx, d, team.name)


async def delete_drill(ctx: Ctx, drill_id: uuid.UUID) -> None:
    """Sessions keep their snapshot of the drill."""
    d = await _drill(ctx, drill_id)
    await get_team(ctx, d.team_id, Action.TRAINING_WRITE)
    await ctx.db.delete(d)
    await audit.record(ctx, "drill.deleted", target_type="club_drill", target_id=d.id)

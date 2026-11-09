from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile, status

from handball_api.models import Consent, Season, Team
from handball_api.routers.deps import OrgDep
from handball_api.schemas.orgs import (
    SeasonCreate,
    SeasonOut,
    TeamCreate,
    TeamMemberOut,
    TeamMemberUpdate,
    TeamOut,
    TeamSettings,
    TeamUpdate,
)
from handball_api.schemas.roster import (
    ConsentCreate,
    ConsentOut,
    ImportResult,
    PlayerStatusIn,
    PlayerStatusOut,
    RosterEntryCreate,
    RosterEntryOut,
    RosterEntryUpdate,
)
from handball_api.services import orgs as service
from handball_api.services import roster as roster_service
from handball_api.services.context import Ctx

router = APIRouter(prefix="/v1/orgs/{org_id}/teams", tags=["teams"])

MAX_CSV_BYTES = 200_000


async def teams_out(ctx: Ctx, teams: list[Team]) -> list[TeamOut]:
    seasons = await service.current_seasons(ctx, [t.id for t in teams])
    return [_team_out(ctx, t, seasons.get(t.id)) for t in teams]


async def team_out(ctx: Ctx, team: Team) -> TeamOut:
    return (await teams_out(ctx, [team]))[0]


def _team_out(ctx: Ctx, team: Team, season: Season | None) -> TeamOut:
    actor = ctx.require_actor()
    return TeamOut(
        id=team.id,
        name=team.name,
        league=team.league,
        is_youth=team.is_youth,
        gender=team.gender,
        settings=TeamSettings(players_see_team_stats=team.players_see_team_stats),
        level=team.level,
        default_format=team.default_format,
        my_role=actor.team_role(team.id),
        current_season=SeasonOut.model_validate(season) if season else None,
        official_team_id=team.official_team_id,
    )


@router.post("", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
async def create_team(data: TeamCreate, scope: OrgDep) -> TeamOut:
    return await team_out(scope.ctx, await service.create_team(scope.ctx, data))


@router.get("", response_model=list[TeamOut])
async def list_teams(scope: OrgDep) -> list[TeamOut]:
    return await teams_out(scope.ctx, await service.list_teams(scope.ctx))


@router.get("/{team_id}", response_model=TeamOut)
async def get_team(team_id: uuid.UUID, scope: OrgDep) -> TeamOut:
    return await team_out(scope.ctx, await service.get_team(scope.ctx, team_id))


@router.patch("/{team_id}", response_model=TeamOut)
async def update_team(team_id: uuid.UUID, data: TeamUpdate, scope: OrgDep) -> TeamOut:
    return await team_out(scope.ctx, await service.update_team(scope.ctx, team_id, data))


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(team_id: uuid.UUID, scope: OrgDep) -> None:
    await service.delete_team(scope.ctx, team_id)


@router.get("/{team_id}/seasons", response_model=list[SeasonOut], tags=["seasons"])
async def list_seasons(team_id: uuid.UUID, scope: OrgDep) -> list[Season]:
    return await service.list_seasons(scope.ctx, team_id)


@router.post(
    "/{team_id}/seasons",
    response_model=SeasonOut,
    status_code=status.HTTP_201_CREATED,
    tags=["seasons"],
)
async def create_season(team_id: uuid.UUID, data: SeasonCreate, scope: OrgDep) -> Season:
    return await service.create_season(scope.ctx, team_id, data)


@router.get("/{team_id}/members", response_model=list[TeamMemberOut], tags=["members"])
async def list_team_members(team_id: uuid.UUID, scope: OrgDep) -> list[TeamMemberOut]:
    return [
        TeamMemberOut(user_id=u.id, name=u.name, email=u.email, role=r)
        for u, r in await service.list_team_members(scope.ctx, team_id)
    ]


@router.patch("/{team_id}/members/{user_id}", response_model=TeamMemberOut, tags=["members"])
async def update_team_member(
    team_id: uuid.UUID, user_id: uuid.UUID, data: TeamMemberUpdate, scope: OrgDep
) -> TeamMemberOut:
    await service.update_team_member(scope.ctx, team_id, user_id, data)
    members = await service.list_team_members(scope.ctx, team_id)
    u, r = next((u, r) for u, r in members if u.id == user_id)
    return TeamMemberOut(user_id=u.id, name=u.name, email=u.email, role=r)


@router.delete(
    "/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["members"]
)
async def remove_team_member(team_id: uuid.UUID, user_id: uuid.UUID, scope: OrgDep) -> None:
    await service.remove_team_member(scope.ctx, team_id, user_id)


@router.get(
    "/{team_id}/seasons/{season_id}/roster", response_model=list[RosterEntryOut], tags=["roster"]
)
async def list_roster(
    team_id: uuid.UUID, season_id: uuid.UUID, scope: OrgDep
) -> list[RosterEntryOut]:
    return await roster_service.list_roster(scope.ctx, team_id, season_id)


@router.post(
    "/{team_id}/seasons/{season_id}/roster",
    response_model=RosterEntryOut,
    status_code=status.HTTP_201_CREATED,
    tags=["roster"],
)
async def add_roster_entry(
    team_id: uuid.UUID, season_id: uuid.UUID, data: RosterEntryCreate, scope: OrgDep
) -> RosterEntryOut:
    return await roster_service.add_entry(scope.ctx, team_id, season_id, data)


@router.post(
    "/{team_id}/seasons/{season_id}/roster/import", response_model=ImportResult, tags=["roster"]
)
async def import_roster(
    team_id: uuid.UUID,
    season_id: uuid.UUID,
    scope: OrgDep,
    file: Annotated[UploadFile, File()],
    dry_run: Annotated[bool, Query()] = True,
) -> ImportResult:
    data = await file.read(MAX_CSV_BYTES + 1)
    return await roster_service.import_csv(scope.ctx, team_id, season_id, data, dry_run)


@router.patch("/{team_id}/roster/{entry_id}", response_model=RosterEntryOut, tags=["roster"])
async def update_roster_entry(
    team_id: uuid.UUID, entry_id: uuid.UUID, data: RosterEntryUpdate, scope: OrgDep
) -> RosterEntryOut:
    return await roster_service.update_entry(scope.ctx, team_id, entry_id, data)


@router.delete(
    "/{team_id}/roster/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["roster"]
)
async def remove_roster_entry(team_id: uuid.UUID, entry_id: uuid.UUID, scope: OrgDep) -> None:
    await roster_service.remove_entry(scope.ctx, team_id, entry_id)


@router.get("/{team_id}/player-statuses", response_model=list[PlayerStatusOut], tags=["roster"])
async def list_player_statuses(team_id: uuid.UUID, scope: OrgDep) -> list[PlayerStatusOut]:
    """Injured and absent players of the squad, still in force (staff)."""
    return await roster_service.list_statuses(scope.ctx, team_id)


@router.put(
    "/{team_id}/players/{player_id}/status", response_model=PlayerStatusOut, tags=["roster"]
)
async def set_player_status(
    team_id: uuid.UUID, player_id: uuid.UUID, data: PlayerStatusIn, scope: OrgDep
) -> PlayerStatusOut:
    """Mark a player injured or absent, optionally until a day (inclusive) and with a note."""
    return await roster_service.set_status(scope.ctx, team_id, player_id, data)


@router.delete(
    "/{team_id}/players/{player_id}/status",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["roster"],
)
async def clear_player_status(team_id: uuid.UUID, player_id: uuid.UUID, scope: OrgDep) -> None:
    """Back to fit (no status)."""
    await roster_service.clear_status(scope.ctx, team_id, player_id)


@router.get(
    "/{team_id}/players/{player_id}/consents", response_model=list[ConsentOut], tags=["consents"]
)
async def list_consents(team_id: uuid.UUID, player_id: uuid.UUID, scope: OrgDep) -> list[Consent]:
    return await roster_service.list_consents(scope.ctx, team_id, player_id)


@router.post(
    "/{team_id}/players/{player_id}/consents",
    response_model=ConsentOut,
    status_code=status.HTTP_201_CREATED,
    tags=["consents"],
)
async def add_consent(
    team_id: uuid.UUID, player_id: uuid.UUID, data: ConsentCreate, scope: OrgDep
) -> Consent:
    return await roster_service.add_consent(scope.ctx, team_id, player_id, data)


@router.delete(
    "/{team_id}/players/{player_id}/consents/{consent_id}",
    response_model=ConsentOut,
    tags=["consents"],
)
async def revoke_consent(
    team_id: uuid.UUID, player_id: uuid.UUID, consent_id: uuid.UUID, scope: OrgDep
) -> Consent:
    return await roster_service.revoke_consent(scope.ctx, team_id, player_id, consent_id)

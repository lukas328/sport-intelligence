from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, File, Query, Response, UploadFile

from handball_api.models import Event
from handball_api.routers.deps import OrgDep
from handball_api.schemas.events import EventIn, EventOut, EventPatch, FeedImportResult, KickoffIn
from handball_api.services import events as service
from handball_api.services import insights as insights_service
from handball_api.services import paper_reports

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["events"])
MAX_IMPORT = 2_000_000


@router.get("/matches/{match_id}/events", response_model=list[EventOut])
async def list_events(
    match_id: uuid.UUID,
    scope: OrgDep,
    side: Annotated[str | None, Query(pattern="^(own|opponent)$")] = None,
    type: Annotated[str | None, Query(max_length=30)] = None,
    outcome: Annotated[str | None, Query(max_length=20)] = None,
    player_id: uuid.UUID | None = None,
    number: Annotated[int | None, Query(ge=0, le=99)] = None,
    zone: Annotated[str | None, Query(max_length=20)] = None,
    goal_zone: Annotated[str | None, Query(max_length=2)] = None,
    turnover_type: Annotated[str | None, Query(max_length=20)] = None,
) -> list[Event]:
    """Filtered event list: every number in the statistics links to these events and clips."""
    return await service.list_events(
        scope.ctx,
        match_id,
        side=side,
        type_=type,
        outcome=outcome,
        player_id=player_id,
        number=number,
        zone=zone,
        goal_zone=goal_zone,
        turnover_type=turnover_type,
    )


@router.post("/matches/{match_id}/events", response_model=EventOut, status_code=201)
async def create_event(match_id: uuid.UUID, data: EventIn, scope: OrgDep) -> Event:
    return await service.create_event(scope.ctx, match_id, data)


@router.patch("/events/{event_id}", response_model=EventOut)
async def update_event(event_id: uuid.UUID, data: EventPatch, scope: OrgDep) -> Event:
    return await service.update_event(scope.ctx, event_id, data)


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(event_id: uuid.UUID, scope: OrgDep) -> None:
    await service.delete_event(scope.ctx, event_id)


@router.get("/matches/{match_id}/stats", response_model=dict[str, Any], tags=["stats"])
async def match_stats(match_id: uuid.UUID, scope: OrgDep) -> dict[str, Any]:
    return await service.match_stats(scope.ctx, match_id)


@router.put("/matches/{match_id}/kickoff", status_code=204)
async def set_kickoff(match_id: uuid.UUID, data: KickoffIn, scope: OrgDep) -> None:
    await service.set_kickoff(scope.ctx, match_id, data.period, data.t_ms)


@router.post("/matches/{match_id}/events/import", response_model=FeedImportResult)
async def import_feed(
    match_id: uuid.UUID, scope: OrgDep, file: Annotated[UploadFile, File()]
) -> dict[str, Any]:
    """Official play-by-play as CSV or JSON (BRIEF 7.4). Nothing is scraped."""
    data = await file.read(MAX_IMPORT + 1)
    return await service.import_feed(
        scope.ctx, match_id, data[:MAX_IMPORT], file.filename or "feed.csv"
    )


@router.post(
    "/teams/{team_id}/paper-reports",
    response_model=dict[str, Any],
    status_code=201,
    tags=["matches"],
)
async def import_paper_report(
    team_id: uuid.UUID, scope: OrgDep, file: Annotated[UploadFile, File()]
) -> dict[str, Any]:
    """Paper match report (docs/schemas/paper-report.schema.json) as a match without video."""
    data = await file.read(MAX_IMPORT + 1)
    return await paper_reports.import_report(scope.ctx, team_id, data[:MAX_IMPORT])


@router.get("/matches/{match_id}/insights", response_model=dict[str, Any], tags=["insights"])
async def match_insights(match_id: uuid.UUID, scope: OrgDep) -> dict[str, Any]:
    """Ranked insights with evidence filters; compared with the other matches of the season."""
    return await insights_service.insights(scope.ctx, match_id)


@router.post("/matches/{match_id}/summary", response_model=dict[str, Any], tags=["insights"])
async def match_summary(match_id: uuid.UUID, scope: OrgDep) -> dict[str, Any]:
    """Prose summary of the insights (Claude API, optional); numbers are verified before saving."""
    return await insights_service.summarise(scope.ctx, match_id)


@router.get(
    "/teams/{team_id}/seasons/{season_id}/stats", response_model=dict[str, Any], tags=["insights"]
)
async def season_stats(team_id: uuid.UUID, season_id: uuid.UUID, scope: OrgDep) -> dict[str, Any]:
    """Per-match key numbers, totals and player totals for a season."""
    return await insights_service.season_stats(scope.ctx, team_id, season_id)


@router.get("/opponents/{opponent_id}/profile", response_model=dict[str, Any], tags=["insights"])
async def opponent_profile(opponent_id: uuid.UUID, scope: OrgDep) -> dict[str, Any]:
    """Scouting profile from all tagged matches against this opponent."""
    return await insights_service.opponent_profile(scope.ctx, opponent_id)


@router.get(
    "/matches/{match_id}/report.pdf",
    response_class=Response,
    tags=["insights"],
    responses={200: {"content": {"application/pdf": {}}}},
)
async def match_report_pdf(
    match_id: uuid.UUID,
    scope: OrgDep,
    lang: Annotated[str, Query(pattern="^(de-CH|en|fr)$")] = "de-CH",
) -> Response:
    """Match report as a PDF for printing and sending."""
    pdf, filename = await insights_service.match_pdf(scope.ctx, match_id, lang)
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"content-disposition": f'attachment; filename="{filename}"'},
    )

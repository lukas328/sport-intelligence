from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, File, Query, Response, UploadFile

from handball_api.models import Event
from handball_api.routers.deps import OrgDep, per_user
from handball_api.schemas.events import (
    EventIn,
    EventOut,
    EventPatch,
    FeedImportResult,
    GoalCandidateList,
    GoalCandidateReviewIn,
    GoalCandidateRow,
    GoalComparison,
    GoalReviewIn,
    KickoffIn,
    OfficialReportIn,
    OfficialReportResult,
)
from handball_api.services import events as service
from handball_api.services import goal_candidates, official_report, paper_reports
from handball_api.services import insights as insights_service

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["events"])
# each import fetches the report from the federation's server (and reads a PDF)
REPORT_LIMIT = (30, 3600)
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


@router.get("/matches/{match_id}/exports/shots", response_model=dict[str, Any], tags=["exports"])
async def shot_export(match_id: uuid.UUID, scope: OrgDep) -> dict[str, Any]:
    """Shots with metadata and goal-camera times (export API for the goalkeeper trainer, P2)."""
    return await service.shot_export(scope.ctx, match_id)


@router.get("/matches/{match_id}/stats", response_model=dict[str, Any], tags=["stats"])
async def match_stats(match_id: uuid.UUID, scope: OrgDep) -> dict[str, Any]:
    """Match statistics (packages/metrics). Each goal counts once: with an imported official report,
    a tagged or video goal of the same side within 20 s of an official goal is that goal.
    `own`/`opponent`: `xg` covers only shots on target with a known position (and penalties),
    `xg_shots` counts them and `xg_coverage` = xg_shots / shots (null without shots); players have
    `xg_shots`, goalkeepers `xg_shots` and `xg_coverage`. Shot zones include `empty_goal`
    (shots on the empty goal, from any distance) apart from `long_range` (over 15 m)."""
    return await service.match_stats(scope.ctx, match_id)


@router.put("/matches/{match_id}/kickoff", status_code=204)
async def set_kickoff(match_id: uuid.UUID, data: KickoffIn, scope: OrgDep) -> None:
    await service.set_kickoff(scope.ctx, match_id, data.period, data.t_ms, data.clock_s)


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
    "/matches/{match_id}/official-report",
    response_model=OfficialReportResult,
    dependencies=[per_user("official-report", REPORT_LIMIT)],
)
async def import_official_report(
    match_id: uuid.UUID, data: OfficialReportIn, scope: OrgDep
) -> dict[str, Any]:
    """Official match report (handball.ch match centre, DHB press report, nuLiga game report of the
    German associations on nuLiga and Austria, HLA report) as events: goals with scorer and shirt
    number, 7-metres, suspensions, time-outs. A re-import replaces the previous
    one; automatic goals from the video within 20 s are merged with the official goal."""
    return await official_report.import_report(scope.ctx, match_id, data.url, data.provider)


@router.get("/matches/{match_id}/official-report/comparison", response_model=GoalComparison)
async def official_goal_comparison(match_id: uuid.UUID, scope: OrgDep) -> dict[str, Any]:
    """Official goals next to the goals the video analysis found (same side, at most 20 s of
    match clock apart), and video goals without an official one, with the coach's checks."""
    return await official_report.comparison(scope.ctx, match_id)


@router.put("/matches/{match_id}/official-report/review", status_code=204)
async def review_official_goal(match_id: uuid.UUID, data: GoalReviewIn, scope: OrgDep) -> None:
    """Confirm or dismiss a row of the comparison (null undoes it)."""
    await official_report.review(scope.ctx, match_id, data.event_id, data.status)


@router.get("/matches/{match_id}/goal-candidates", response_model=GoalCandidateList)
async def list_goal_candidates(
    match_id: uuid.UUID, scope: OrgDep, kind: Literal["goal", "shot"] = "goal"
) -> dict[str, Any]:
    """Moments of the video that are probably goals (kind=shot: shots of any outcome; video
    analysis, a fixed number per minute), with the coach's reviews, the shots already stored that
    cover them and, for shots, the official report's suggestion."""
    return await goal_candidates.listing(scope.ctx, match_id, kind)


@router.get("/matches/{match_id}/shot-candidates", response_model=GoalCandidateList)
async def list_shot_candidates(match_id: uuid.UUID, scope: OrgDep) -> dict[str, Any]:
    """The shot candidates (goal-candidates?kind=shot) with the official report's shots on the
    video."""
    return await goal_candidates.listing(scope.ctx, match_id, "shot")


@router.put(
    "/matches/{match_id}/goal-candidates/{candidate_id}/review", response_model=GoalCandidateRow
)
async def review_goal_candidate(
    match_id: uuid.UUID, candidate_id: uuid.UUID, data: GoalCandidateReviewIn, scope: OrgDep
) -> dict[str, Any]:
    """Confirm a candidate (a shot of the given side and outcome; a report entry is pinned to
    the video instead of a second event), reject it (kept as a hard negative for training) or
    undo the review (null)."""
    return await goal_candidates.review(
        scope.ctx,
        match_id,
        candidate_id,
        data.status,
        data.side,
        data.outcome,
        data.official_event_id,
        data.number,
        data.player_id,
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
    """Per-match key numbers, totals and player totals for a season. Every played match counts (a
    result stored or events): rows have `tagged`, `goals`/`goals_against` from the events (from the
    result when untagged) and `xg_coverage`; totals have `matches`, `tagged_matches`, `xg`,
    `xg_shots` and `xg_coverage` = shots with xG / shots on target (null without shots), and
    shooting/save percentages only from matches with recorded misses or saves."""
    return await insights_service.season_stats(scope.ctx, team_id, season_id)


@router.get("/opponents/{opponent_id}/profile", response_model=dict[str, Any], tags=["insights"])
async def opponent_profile(opponent_id: uuid.UUID, scope: OrgDep) -> dict[str, Any]:
    """Scouting profile from all tagged matches against this opponent. `matches` rows carry
    `is_home` (our home game); `totals` carry `xg_shots` and `xg_coverage` like the season stats."""
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

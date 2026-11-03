"""Player feed "Deine Szenen" and self-assessment (addendum 01, 4.7)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query

from handball_api.routers.deps import OrgDep
from handball_api.schemas.feed import (
    CoachFeedPlayer,
    FeedComment,
    FeedGenerated,
    FeedListItem,
    FeedSwap,
    PlayerFeed,
    SelfAssessmentIn,
)
from handball_api.services import feed as service

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["feed"])


@router.post("/matches/{match_id}/feed/generate", response_model=FeedGenerated)
async def generate(match_id: uuid.UUID, scope: OrgDep) -> FeedGenerated:
    """Rebuilds the scenes of all players (runs automatically after every analysis)."""
    return FeedGenerated(players=await service.generate_now(scope.ctx, match_id))


@router.get("/matches/{match_id}/feed", response_model=list[CoachFeedPlayer])
async def team_feed(match_id: uuid.UUID, scope: OrgDep) -> list[dict[str, Any]]:
    """Coach overview: scenes per player and self-assessments."""
    return await service.team_feed(scope.ctx, match_id)


@router.patch("/feed-items/{item_id}", status_code=204)
async def comment(item_id: uuid.UUID, data: FeedComment, scope: OrgDep) -> None:
    await service.comment(scope.ctx, item_id, data.coach_comment)


@router.put("/feed-items/{item_id}/scene", status_code=204)
async def swap(item_id: uuid.UUID, data: FeedSwap, scope: OrgDep) -> None:
    await service.swap(scope.ctx, item_id, data.event_id)


@router.get("/me/feeds", response_model=list[FeedListItem])
async def my_feeds(scope: OrgDep) -> list[dict[str, Any]]:
    return await service.my_feeds(scope.ctx)


@router.get("/matches/{match_id}/feed/me", response_model=PlayerFeed)
async def player_feed(
    match_id: uuid.UUID, scope: OrgDep, player_id: Annotated[uuid.UUID | None, Query()] = None
) -> dict[str, Any]:
    """My scenes (or my child's). Coach comments appear after the self-assessment."""
    return await service.player_feed(scope.ctx, match_id, player_id)


@router.put("/matches/{match_id}/self-assessment", response_model=PlayerFeed)
async def assess(match_id: uuid.UUID, data: SelfAssessmentIn, scope: OrgDep) -> dict[str, Any]:
    return await service.assess(scope.ctx, match_id, data.rating, data.text, data.player_id)

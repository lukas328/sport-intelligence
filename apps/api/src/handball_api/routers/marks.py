"""Courtside marks with device time and automatic video sync (addendum 01, 5.3)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter

from handball_api.models import LiveTagSession
from handball_api.routers.deps import OrgDep
from handball_api.schemas.marks import (
    MarkKey,
    MarkKeysIn,
    MarkSessionIn,
    MarkSessionOut,
    MarksIn,
    MatchMarks,
    OffsetIn,
    SyncOut,
)
from handball_api.services import marks as service

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["marks"])


@router.get("/teams/{team_id}/mark-keys", response_model=list[MarkKey])
async def keys(team_id: uuid.UUID, scope: OrgDep) -> list[dict[str, Any]]:
    """The team's 4 to 8 buttons; goal_own and goal_opp make the automatic sync possible."""
    return await service.keys(scope.ctx, team_id)


@router.put("/teams/{team_id}/mark-keys", response_model=list[MarkKey])
async def set_keys(team_id: uuid.UUID, body: MarkKeysIn, scope: OrgDep) -> list[dict[str, Any]]:
    return await service.set_keys(scope.ctx, team_id, body.keys)


@router.post("/matches/{match_id}/mark-sessions", response_model=MarkSessionOut, status_code=201)
async def start(match_id: uuid.UUID, body: MarkSessionIn, scope: OrgDep) -> LiveTagSession:
    return await service.start(scope.ctx, match_id, body.device)


@router.post("/mark-sessions/{session_id}/marks")
async def add(session_id: uuid.UUID, body: MarksIn, scope: OrgDep) -> dict[str, Any]:
    """Uploads marks saved offline; a mark with a known client id is not stored twice."""
    return await service.add(scope.ctx, session_id, body.marks)


@router.delete("/matches/{match_id}/marks/{client_id}", status_code=204)
async def take_back(match_id: uuid.UUID, client_id: uuid.UUID, scope: OrgDep) -> None:
    """«Zurücknehmen» on the Spieltag: the mark with this phone id is removed (UX test N14)."""
    await service.take_back(scope.ctx, match_id, client_id)


@router.put("/mark-sessions/{session_id}/offset", response_model=MarkSessionOut)
async def offset(session_id: uuid.UUID, body: OffsetIn, scope: OrgDep) -> LiveTagSession:
    return await service.set_offset(scope.ctx, session_id, body.offset_ms)


@router.post("/matches/{match_id}/marks/sync", response_model=list[SyncOut])
async def sync(match_id: uuid.UUID, scope: OrgDep) -> list[dict[str, Any]]:
    return await service.sync_match(scope.ctx, match_id)


@router.get("/matches/{match_id}/marks", response_model=MatchMarks)
async def marks(match_id: uuid.UUID, scope: OrgDep) -> dict[str, Any]:
    """Marks of all phones with their video time once synced, split at the half-time mark."""
    return await service.marks(scope.ctx, match_id)

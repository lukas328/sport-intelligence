from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import Field

from handball_api.routers.deps import OrgDep
from handball_api.schemas.common import ApiModel
from handball_api.services import collections as service

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["collections"])

Source = Literal["collection", "playlist", "presentation", "assignment"]


class ItemIn(ApiModel):
    kind: Literal["scene", "play", "note"]
    text: str | None = Field(default=None, max_length=4000)
    # a scene: an existing clip, an event (window around it) or a match window
    clip_id: uuid.UUID | None = None
    event_id: uuid.UUID | None = None
    match_id: uuid.UUID | None = None
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    title: str | None = Field(default=None, max_length=200)
    play_id: uuid.UUID | None = None


class SceneOut(ApiModel):
    clip_id: uuid.UUID
    match_id: uuid.UUID
    start_ms: int
    end_ms: int
    title: str | None
    event_id: uuid.UUID | None = None


class PlayRef(ApiModel):
    id: uuid.UUID
    name: str


class ItemOut(ApiModel):
    position: int
    kind: Literal["scene", "play", "note"]
    text: str | None
    scene: SceneOut | None
    play: PlayRef | None


class CollectionSummary(ApiModel):
    id: uuid.UUID
    title: str
    source: Source = Field(description="collection, or the older object read as one")
    entries: int
    draft: bool
    created_at: datetime


class CollectionOut(ApiModel):
    id: uuid.UUID
    team_id: uuid.UUID
    title: str
    source: Source
    editable: bool = Field(description="only collections; older objects change where they are")
    draft: bool
    match_id: uuid.UUID | None
    created_at: datetime
    items: list[ItemOut]


class CollectionCreate(ApiModel):
    title: str = Field(min_length=1, max_length=200)
    items: list[ItemIn] = Field(default_factory=list, max_length=200)


class CollectionPatch(ApiModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    draft: bool | None = None
    items: list[ItemIn] | None = Field(default=None, max_length=200)


class FromMatch(ApiModel):
    match_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)


def _items(items: list[ItemIn] | None) -> list[dict[str, Any]] | None:
    return None if items is None else [i.model_dump() for i in items]


@router.get("/teams/{team_id}/collections", response_model=list[CollectionSummary])
async def list_collections(team_id: uuid.UUID, scope: OrgDep) -> list[dict[str, Any]]:
    """Collections of the team; playlists, presentations and assignments are listed as ones."""
    return await service.list_for_team(scope.ctx, team_id)


@router.post("/teams/{team_id}/collections", response_model=CollectionOut, status_code=201)
async def create_collection(team_id: uuid.UUID, data: CollectionCreate, scope: OrgDep) -> Any:
    c = await service.create(scope.ctx, team_id, data.title, _items(data.items) or [])
    return await service.get(scope.ctx, c.id)


@router.post(
    "/teams/{team_id}/collections/from-match", response_model=CollectionOut, status_code=201
)
async def collection_from_match(team_id: uuid.UUID, data: FromMatch, scope: OrgDep) -> Any:
    """'Fürs Team zusammenstellen': a draft with the scenes behind the three things of a match."""
    c = await service.from_match(scope.ctx, team_id, data.match_id, data.title)
    return await service.get(scope.ctx, c.id)


@router.get("/collections/{collection_id}", response_model=CollectionOut)
async def get_collection(collection_id: uuid.UUID, scope: OrgDep) -> Any:
    """A collection, or a playlist, presentation or assignment read as one (by its id)."""
    return await service.get(scope.ctx, collection_id)


@router.patch("/collections/{collection_id}", response_model=CollectionOut)
async def update_collection(collection_id: uuid.UUID, data: CollectionPatch, scope: OrgDep) -> Any:
    """Title, draft state, entries (the whole ordered list). Older objects: 409 read-only-source."""
    await service.update(
        scope.ctx, collection_id, title=data.title, draft=data.draft, items=_items(data.items)
    )
    return await service.get(scope.ctx, collection_id)


@router.delete("/collections/{collection_id}", status_code=204)
async def delete_collection(collection_id: uuid.UUID, scope: OrgDep) -> None:
    await service.delete(scope.ctx, collection_id)

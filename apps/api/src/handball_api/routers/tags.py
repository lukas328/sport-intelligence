"""Own tags, search and smart playlists (addendum 01, 4.4)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from handball_api.models import SavedFilter, Tag, TagSet
from handball_api.routers.deps import OrgDep
from handball_api.schemas.tags import (
    MatchTagLinks,
    SavedFilterIn,
    SavedFilterOut,
    SearchFilter,
    SearchResult,
    TagIn,
    TagLinksIn,
    TagOut,
    TagPatch,
    TagSetIn,
    TagSetOut,
)
from handball_api.services import tags as service

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["tags"])


def _set_out(ts: TagSet, tags: list[Tag]) -> TagSetOut:
    return TagSetOut(id=ts.id, name=ts.name, tags=[TagOut.model_validate(t) for t in tags])


def _filter_out(sf: SavedFilter) -> SavedFilterOut:
    return SavedFilterOut(
        id=sf.id,
        name=sf.name,
        query=SearchFilter.model_validate(sf.query),
        created_at=sf.created_at,
    )


@router.get("/teams/{team_id}/tag-sets", response_model=list[TagSetOut])
async def list_tag_sets(team_id: uuid.UUID, scope: OrgDep) -> list[TagSetOut]:
    return [_set_out(s, t) for s, t in await service.tag_sets(scope.ctx, team_id)]


@router.post("/teams/{team_id}/tag-sets", response_model=TagSetOut, status_code=201)
async def create_tag_set(team_id: uuid.UUID, data: TagSetIn, scope: OrgDep) -> TagSetOut:
    ts = await service.create_tag_set(scope.ctx, team_id, data)
    return next(
        _set_out(s, t) for s, t in await service.tag_sets(scope.ctx, team_id) if s.id == ts.id
    )


@router.patch("/tag-sets/{tag_set_id}", status_code=204)
async def rename_tag_set(tag_set_id: uuid.UUID, data: TagPatch, scope: OrgDep) -> None:
    if data.name:
        await service.rename_tag_set(scope.ctx, tag_set_id, data.name)


@router.delete("/tag-sets/{tag_set_id}", status_code=204)
async def delete_tag_set(tag_set_id: uuid.UUID, scope: OrgDep) -> None:
    await service.delete_tag_set(scope.ctx, tag_set_id)


@router.post("/tag-sets/{tag_set_id}/tags", response_model=TagOut, status_code=201)
async def add_tag(tag_set_id: uuid.UUID, data: TagIn, scope: OrgDep) -> Tag:
    return await service.add_tag(scope.ctx, tag_set_id, data)


@router.patch("/tags/{tag_id}", response_model=TagOut)
async def update_tag(tag_id: uuid.UUID, data: TagPatch, scope: OrgDep) -> Tag:
    return await service.update_tag(scope.ctx, tag_id, data)


@router.delete("/tags/{tag_id}", status_code=204)
async def delete_tag(tag_id: uuid.UUID, scope: OrgDep) -> None:
    await service.delete_tag(scope.ctx, tag_id)


@router.put("/tag-links", response_model=list[uuid.UUID])
async def set_links(data: TagLinksIn, scope: OrgDep) -> list[uuid.UUID]:
    """Sets the team tags of a clip, event or play (replaces the previous tags)."""
    return await service.set_links(scope.ctx, data)


@router.get("/matches/{match_id}/tag-links", response_model=MatchTagLinks)
async def match_links(match_id: uuid.UUID, scope: OrgDep) -> MatchTagLinks:
    links = await service.match_links(scope.ctx, match_id)
    return MatchTagLinks(clips=links["clips"], events=links["events"])


@router.post("/teams/{team_id}/search", response_model=SearchResult)
async def search(team_id: uuid.UUID, data: SearchFilter, scope: OrgDep) -> SearchResult:
    """Events and clips by automatic attributes and own tags, with video windows."""
    return await service.search(scope.ctx, team_id, data)


@router.get("/teams/{team_id}/saved-filters", response_model=list[SavedFilterOut])
async def list_filters(team_id: uuid.UUID, scope: OrgDep) -> list[SavedFilterOut]:
    return [_filter_out(f) for f in await service.saved_filters(scope.ctx, team_id)]


@router.post("/teams/{team_id}/saved-filters", response_model=SavedFilterOut, status_code=201)
async def save_filter(team_id: uuid.UUID, data: SavedFilterIn, scope: OrgDep) -> SavedFilterOut:
    return _filter_out(await service.save_filter(scope.ctx, team_id, data))


@router.delete("/saved-filters/{filter_id}", status_code=204)
async def delete_filter(filter_id: uuid.UUID, scope: OrgDep) -> None:
    await service.delete_filter(scope.ctx, filter_id)


@router.get("/saved-filters/{filter_id}/results", response_model=SearchResult)
async def run_filter(filter_id: uuid.UUID, scope: OrgDep) -> SearchResult:
    """Smart playlist: evaluated on every call, new matches appear automatically."""
    return await service.run_filter(scope.ctx, filter_id)

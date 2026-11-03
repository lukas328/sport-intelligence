"""Presentation mode for the video session (addendum 01, 4.1)."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse

from handball_api.core.db import open_session, set_current_user
from handball_api.core.errors import ProblemError
from handball_api.models import Presentation, PresentationSlide
from handball_api.routers.deps import OrgDep
from handball_api.schemas.presentations import (
    PresentationDetail,
    PresentationIn,
    PresentationOut,
    PresentationPatch,
    RemoteCommand,
    RemotePairing,
    SlideIn,
    SlideOrder,
    SlideOut,
    SlidePatch,
)
from handball_api.services import auth as auth_service
from handball_api.services import orgs as org_service
from handball_api.services import presentations as service
from handball_api.services.context import Ctx

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["presentations"])


def _out(p: Presentation, n: int) -> PresentationOut:
    return PresentationOut(
        id=p.id,
        team_id=p.team_id,
        match_id=p.match_id,
        title=p.title,
        shared_with_players=p.shared_with_players,
        slides=n,
        export_status=p.export_status,
        created_at=p.created_at,
    )


async def _detail(scope: Any, pres_id: uuid.UUID) -> PresentationDetail:
    p, slides, can_edit = await service.detail(scope.ctx, pres_id)
    return PresentationDetail(
        **_out(p, len(slides)).model_dump(),
        slide_list=[SlideOut.model_validate(s) for s in slides],
        can_edit=can_edit,
    )


@router.get("/teams/{team_id}/presentations", response_model=list[PresentationOut])
async def list_presentations(team_id: uuid.UUID, scope: OrgDep) -> list[PresentationOut]:
    return [_out(p, n) for p, n in await service.list_for_team(scope.ctx, team_id)]


@router.post("/teams/{team_id}/presentations", response_model=PresentationDetail, status_code=201)
async def create(team_id: uuid.UUID, data: PresentationIn, scope: OrgDep) -> PresentationDetail:
    p = await service.create(scope.ctx, team_id, data)
    return await _detail(scope, p.id)


@router.post(
    "/scouting/{report_id}/presentation", response_model=PresentationDetail, status_code=201
)
async def from_scouting(report_id: uuid.UUID, scope: OrgDep) -> PresentationDetail:
    """The preparation report as a presentation (observations, then their clips)."""
    p = await service.from_scouting(scope.ctx, report_id)
    return await _detail(scope, p.id)


@router.get("/presentations/{pres_id}", response_model=PresentationDetail)
async def get(pres_id: uuid.UUID, scope: OrgDep) -> PresentationDetail:
    return await _detail(scope, pres_id)


@router.patch("/presentations/{pres_id}", response_model=PresentationDetail)
async def update(pres_id: uuid.UUID, data: PresentationPatch, scope: OrgDep) -> PresentationDetail:
    await service.update(scope.ctx, pres_id, data)
    return await _detail(scope, pres_id)


@router.delete("/presentations/{pres_id}", status_code=204)
async def delete(pres_id: uuid.UUID, scope: OrgDep) -> None:
    await service.delete(scope.ctx, pres_id)


@router.post("/presentations/{pres_id}/slides", response_model=SlideOut, status_code=201)
async def add_slide(pres_id: uuid.UUID, data: SlideIn, scope: OrgDep) -> PresentationSlide:
    return await service.add_slide(scope.ctx, pres_id, data)


@router.patch("/slides/{slide_id}", response_model=SlideOut)
async def update_slide(slide_id: uuid.UUID, data: SlidePatch, scope: OrgDep) -> PresentationSlide:
    return await service.update_slide(scope.ctx, slide_id, data)


@router.delete("/slides/{slide_id}", status_code=204)
async def delete_slide(slide_id: uuid.UUID, scope: OrgDep) -> None:
    await service.delete_slide(scope.ctx, slide_id)


@router.put("/presentations/{pres_id}/order", response_model=PresentationDetail)
async def reorder(pres_id: uuid.UUID, data: SlideOrder, scope: OrgDep) -> PresentationDetail:
    await service.reorder(scope.ctx, pres_id, data.slide_ids)
    return await _detail(scope, pres_id)


@router.put("/slides/{slide_id}/image", status_code=204)
async def set_image(slide_id: uuid.UUID, file: UploadFile, scope: OrgDep) -> None:
    await service.set_image(scope.ctx, slide_id, await file.read(3 * 1024 * 1024 + 1))


@router.get(
    "/slides/{slide_id}/image",
    response_class=Response,
    responses={200: {"content": {"image/png": {}, "image/jpeg": {}}}},
)
async def get_image(slide_id: uuid.UUID, scope: OrgDep) -> Response:
    data, ctype = await service.get_image(scope.ctx, slide_id)
    return Response(data, media_type=ctype, headers={"cache-control": "private, max-age=3600"})


@router.post("/presentations/{pres_id}/export", response_model=PresentationDetail, status_code=202)
async def start_export(pres_id: uuid.UUID, scope: OrgDep) -> PresentationDetail:
    """MP4 with burned-in drawings, rendered by the worker."""
    await service.start_export(scope.ctx, pres_id)
    return await _detail(scope, pres_id)


@router.get(
    "/presentations/{pres_id}/export.mp4",
    response_class=Response,
    responses={200: {"content": {"video/mp4": {}}}},
)
async def export_file(pres_id: uuid.UUID, scope: OrgDep) -> Response:
    data = await service.export_file(scope.ctx, pres_id)
    return Response(
        data,
        media_type="video/mp4",
        headers={"content-disposition": 'attachment; filename="praesentation.mp4"'},
    )


@router.get(
    "/presentations/{pres_id}/pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def pdf(
    pres_id: uuid.UUID,
    scope: OrgDep,
    lang: Annotated[str, Query(pattern="^(de-CH|en|fr)$")] = "de-CH",
) -> Response:
    """Stills plus notes per slide."""
    return Response(await service.pdf(scope.ctx, pres_id, lang), media_type="application/pdf")


@router.post("/presentations/{pres_id}/remote", response_model=RemotePairing)
async def pair(pres_id: uuid.UUID, scope: OrgDep) -> RemotePairing:
    """Pairing key for the phone remote (shown as QR code by the presenter)."""
    return RemotePairing(
        key=await service.pair(scope.ctx, pres_id), expires_in_s=service.REMOTE_TTL_S
    )


@router.post("/presentations/{pres_id}/remote/command", status_code=204)
async def command(pres_id: uuid.UUID, data: RemoteCommand, scope: OrgDep) -> None:
    await service.command(
        scope.ctx, pres_id, data.key, data.model_dump(exclude={"key"}, exclude_none=True)
    )


@router.get(
    "/presentations/{pres_id}/remote/stream",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def remote_stream(
    request: Request,
    org_id: Annotated[uuid.UUID, Path()],
    pres_id: uuid.UUID,
    key: Annotated[str, Query(min_length=16, max_length=64)],
) -> StreamingResponse:
    """Commands of the paired phone as Server-Sent Events. Authorises once, then holds no
    database connection while streaming."""
    app = request.app
    settings = app.state.settings
    token = request.cookies.get(settings.session_cookie)
    async with open_session() as db:
        ctx = Ctx(db=db, settings=settings, email=app.state.email, storage=app.state.storage)
        found = await auth_service.resolve_session(ctx, token) if token else None
        if found is None or found[0].mfa_pending:
            raise ProblemError(401, "unauthenticated", "Please sign in")
        await set_current_user(db, found[1].id)
        ctx.actor, _ = await org_service.build_actor(ctx, found[1], org_id)
        await service.detail(ctx, pres_id)
    bus = app.state.events
    channel = service.channel(pres_id, key)

    async def stream() -> AsyncIterator[str]:
        yield "event: ready\ndata: {}\n\n"
        events = bus.subscribe(channel)
        nxt: asyncio.Task[Any] | None = None
        try:
            while not await request.is_disconnected():
                nxt = nxt or asyncio.ensure_future(anext(events))
                done, _ = await asyncio.wait({nxt}, timeout=15)
                if done:
                    yield f"event: command\ndata: {json.dumps(nxt.result(), default=str)}\n\n"
                    nxt = None
                else:
                    yield ": keep-alive\n\n"
        finally:
            if nxt:
                nxt.cancel()
            await events.aclose()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"cache-control": "no-store", "x-accel-buffering": "no"},
    )

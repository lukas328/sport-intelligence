"""Training sessions, attendance and calendar feed (addendum 01, 5.7)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, File, Query, Response, UploadFile

from handball_api.models import TrainingSession
from handball_api.routers.deps import CtxDep, OrgDep
from handball_api.schemas.sessions import (
    AttendanceIn,
    AttendanceRow,
    CalendarLink,
    MyReply,
    ScheduleItem,
    TrainingSessionIn,
    TrainingSessionOut,
)
from handball_api.services import sessions as service

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["training"])
public = APIRouter(prefix="/v1/calendar", tags=["training"])
Kind = Literal["session", "match"]
Lang = Annotated[Literal["de-CH", "en", "fr"], Query()]


def _out(s: TrainingSession) -> TrainingSessionOut:
    return TrainingSessionOut.model_validate(
        {
            "id": s.id,
            "team_id": s.team_id,
            "on_date": s.on_date,
            "starts_at": s.starts_at,
            "title": s.title,
            "location": s.location,
            "notes": s.notes,
            "drills": s.drills,
            "total_minutes": service.total_minutes(s),
            "external_ref": s.external_ref,
        }
    )


@router.get("/teams/{team_id}/sessions", response_model=list[TrainingSessionOut])
async def sessions(
    team_id: uuid.UUID,
    scope: OrgDep,
    start: Annotated[date | None, Query(alias="from")] = None,
    end: Annotated[date | None, Query(alias="to")] = None,
) -> list[TrainingSessionOut]:
    return [_out(s) for s in await service.list_sessions(scope.ctx, team_id, start, end)]


@router.post("/teams/{team_id}/sessions", response_model=TrainingSessionOut, status_code=201)
async def create(team_id: uuid.UUID, body: TrainingSessionIn, scope: OrgDep) -> TrainingSessionOut:
    return _out(await service.create_session(scope.ctx, team_id, body))


@router.get("/sessions/{session_id}", response_model=TrainingSessionOut)
async def get(session_id: uuid.UUID, scope: OrgDep) -> TrainingSessionOut:
    return _out(await service.get_session(scope.ctx, session_id))


@router.put("/sessions/{session_id}", response_model=TrainingSessionOut)
async def update(
    session_id: uuid.UUID, body: TrainingSessionIn, scope: OrgDep
) -> TrainingSessionOut:
    return _out(await service.update_session(scope.ctx, session_id, body))


@router.delete("/sessions/{session_id}", status_code=204)
async def delete(session_id: uuid.UUID, scope: OrgDep) -> Response:
    await service.delete_session(scope.ctx, session_id)
    return Response(status_code=204)


@router.get(
    "/sessions/{session_id}/pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def pdf(session_id: uuid.UUID, scope: OrgDep, lang: Lang = "de-CH") -> Response:
    """The session plan for the hall."""
    data, name = await service.session_pdf(scope.ctx, session_id, lang)
    return Response(
        data,
        media_type="application/pdf",
        headers={"content-disposition": f'inline; filename="{name}"'},
    )


@router.get("/attendance/{kind}/{target_id}", response_model=list[AttendanceRow])
async def attendance(kind: Kind, target_id: uuid.UUID, scope: OrgDep) -> list[dict[str, Any]]:
    return await service.attendance(scope.ctx, kind, target_id)


@router.put("/attendance/{kind}/{target_id}", response_model=list[AttendanceRow])
async def record(
    kind: Kind, target_id: uuid.UUID, body: AttendanceIn, scope: OrgDep
) -> list[dict[str, Any]]:
    """Staff record who was there after the session or match."""
    return await service.record(scope.ctx, kind, target_id, body.records)


@router.get("/me/schedule", response_model=list[ScheduleItem])
async def schedule(scope: OrgDep) -> list[dict[str, Any]]:
    """Upcoming sessions and matches of me and my children, with my replies."""
    return await service.my_schedule(scope.ctx)


@router.put("/me/attendance")
async def reply(body: MyReply, scope: OrgDep) -> dict[str, Any]:
    return await service.reply(scope.ctx, body)


@router.post("/teams/{team_id}/calendar", response_model=CalendarLink, status_code=201)
async def calendar_link(team_id: uuid.UUID, scope: OrgDep) -> CalendarLink:
    """A new subscription link (the old one stops working); shown only now."""
    token = await service.new_calendar_token(scope.ctx, team_id)
    base = scope.ctx.settings.web_base_url.rstrip("/")
    return CalendarLink(url=f"{base}/v1/calendar/{token}.ics")


@router.delete("/teams/{team_id}/calendar", status_code=204)
async def calendar_revoke(team_id: uuid.UUID, scope: OrgDep) -> Response:
    await service.revoke_calendar(scope.ctx, team_id)
    return Response(status_code=204)


@router.post("/teams/{team_id}/sessions/import")
async def import_ics(
    team_id: uuid.UUID, scope: OrgDep, file: Annotated[UploadFile, File()]
) -> dict[str, int]:
    """Sessions from an ICS calendar file (Spond, club calendar)."""
    return await service.import_ics(scope.ctx, team_id, await file.read(service.MAX_ICS_BYTES + 1))


@public.get(
    "/{token}.ics",
    response_class=Response,
    responses={200: {"content": {"text/calendar": {}}}},
)
async def feed(token: str, ctx: CtxDep) -> Response:
    """Calendar feed for calendar apps; the token is the only credential."""
    body = await service.calendar_ics(ctx, token)
    return Response(
        body,
        media_type="text/calendar; charset=utf-8",
        headers={"cache-control": "private, max-age=900"},
    )

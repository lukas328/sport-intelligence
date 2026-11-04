from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from handball_api.core.db import open_session, set_current_user
from handball_api.core.errors import ProblemError
from handball_api.models import (
    Annotation,
    Clip,
    Opponent,
    OpponentPlayer,
    Playlist,
    ProcessingJob,
    Track,
)
from handball_api.routers.deps import CtxDep, OrgDep
from handball_api.schemas.matches import (
    AnalysisOut,
    AnnotationCreate,
    AnnotationOut,
    CalibrationIn,
    ClipCreate,
    ClipOut,
    CommentCreate,
    CommentOut,
    LinkImport,
    MatchCreate,
    MatchOut,
    MatchSummary,
    MatchUpdate,
    OpponentCreate,
    OpponentOut,
    OpponentPlayerIn,
    OpponentPlayerOut,
    OpponentUpdate,
    PartsRequest,
    PartUrl,
    PlaylistCreate,
    PlaylistDetail,
    PlaylistItemCreate,
    PlaylistOut,
    PlaylistUpdate,
    ReorderIn,
    TrackIdentity,
    TrackOut,
    UploadComplete,
    UploadCreate,
    UploadedPartOut,
    UploadOut,
    VideoOut,
    VideoUpdate,
)
from handball_api.services import auth as auth_service
from handball_api.services import matches as service
from handball_api.services import media, videos
from handball_api.services import orgs as org_service
from handball_api.services.context import Ctx

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["matches"])


# ---- opponents -----------------------------------------------------------------------------


@router.get("/opponents", response_model=list[OpponentOut], tags=["opponents"])
async def list_opponents(scope: OrgDep) -> list[Opponent]:
    return await service.list_opponents(scope.ctx)


@router.post("/opponents", response_model=OpponentOut, status_code=201, tags=["opponents"])
async def create_opponent(data: OpponentCreate, scope: OrgDep) -> Opponent:
    return await service.create_opponent(scope.ctx, data)


@router.patch("/opponents/{opponent_id}", response_model=OpponentOut, tags=["opponents"])
async def update_opponent(opponent_id: uuid.UUID, data: OpponentUpdate, scope: OrgDep) -> Opponent:
    return await service.update_opponent(scope.ctx, opponent_id, data)


@router.get(
    "/opponents/{opponent_id}/players",
    response_model=list[OpponentPlayerOut],
    tags=["opponents"],
)
async def opponent_players(opponent_id: uuid.UUID, scope: OrgDep) -> list[OpponentPlayer]:
    """Opponent players: number only by default; names only from public sources (internal)."""
    return await service.opponent_players(scope.ctx, opponent_id)


@router.put(
    "/opponents/{opponent_id}/players",
    response_model=list[OpponentPlayerOut],
    tags=["opponents"],
)
async def put_opponent_players(
    opponent_id: uuid.UUID, data: list[OpponentPlayerIn], scope: OrgDep
) -> list[OpponentPlayer]:
    return await service.put_opponent_players(scope.ctx, opponent_id, data)


# ---- matches -------------------------------------------------------------------------------


@router.get("/teams/{team_id}/matches", response_model=list[MatchSummary])
async def list_matches(
    team_id: uuid.UUID, scope: OrgDep, season_id: Annotated[uuid.UUID | None, Query()] = None
) -> list[MatchSummary]:
    return await service.list_matches(scope.ctx, team_id, season_id)


@router.post("/teams/{team_id}/matches", response_model=MatchOut, status_code=201)
async def create_match(team_id: uuid.UUID, data: MatchCreate, scope: OrgDep) -> MatchOut:
    return await service.match_out(scope.ctx, await service.create_match(scope.ctx, team_id, data))


@router.get("/matches/{match_id}", response_model=MatchOut)
async def get_match(match_id: uuid.UUID, scope: OrgDep) -> MatchOut:
    return await service.match_out(scope.ctx, await service.get_match(scope.ctx, match_id))


@router.patch("/matches/{match_id}", response_model=MatchOut)
async def update_match(match_id: uuid.UUID, data: MatchUpdate, scope: OrgDep) -> MatchOut:
    return await service.match_out(scope.ctx, await service.update_match(scope.ctx, match_id, data))


@router.delete("/matches/{match_id}", status_code=204)
async def delete_match(match_id: uuid.UUID, scope: OrgDep) -> None:
    await service.delete_match(scope.ctx, match_id)


# ---- videos --------------------------------------------------------------------------------


@router.post(
    "/matches/{match_id}/videos", response_model=UploadOut, status_code=201, tags=["videos"]
)
async def create_upload(match_id: uuid.UUID, data: UploadCreate, scope: OrgDep) -> UploadOut:
    asset, part_size, count = await videos.create_upload(scope.ctx, match_id, data)
    return UploadOut(video=service.video_out(asset), part_size=part_size, part_count=count)


@router.post(
    "/matches/{match_id}/videos/import", response_model=VideoOut, status_code=202, tags=["videos"]
)
async def import_video(match_id: uuid.UUID, data: LinkImport, scope: OrgDep) -> VideoOut:
    return service.video_out(await videos.import_link(scope.ctx, match_id, data))


@router.post("/videos/{video_id}/parts", response_model=list[PartUrl], tags=["videos"])
async def presign_parts(video_id: uuid.UUID, data: PartsRequest, scope: OrgDep) -> list[PartUrl]:
    return [
        PartUrl(number=n, url=u)
        for n, u in await videos.presign_parts(scope.ctx, video_id, data.numbers)
    ]


@router.get("/videos/{video_id}/parts", response_model=list[UploadedPartOut], tags=["videos"])
async def list_parts(video_id: uuid.UUID, scope: OrgDep) -> list[UploadedPartOut]:
    return [
        UploadedPartOut(number=n, etag=e, size=s)
        for n, e, s in await videos.list_parts(scope.ctx, video_id)
    ]


@router.post("/videos/{video_id}/complete", response_model=VideoOut, tags=["videos"])
async def complete_upload(video_id: uuid.UUID, data: UploadComplete, scope: OrgDep) -> VideoOut:
    return service.video_out(await videos.complete_upload(scope.ctx, video_id, data))


@router.patch("/videos/{video_id}", response_model=VideoOut, tags=["videos"])
async def update_video(video_id: uuid.UUID, data: VideoUpdate, scope: OrgDep) -> VideoOut:
    return service.video_out(await videos.set_offset(scope.ctx, video_id, data.time_offset_ms))


@router.post("/videos/{video_id}/reprocess", status_code=202, tags=["videos"])
async def reprocess(video_id: uuid.UUID, scope: OrgDep) -> dict[str, str]:
    job = await videos.reprocess(scope.ctx, video_id)
    return {"job_id": str(job.id)}


@router.delete("/videos/{video_id}", status_code=204, tags=["videos"])
async def delete_video(video_id: uuid.UUID, scope: OrgDep) -> None:
    await videos.abort_upload(scope.ctx, video_id)


@router.get(
    "/videos/{video_id}/media/{path:path}",
    tags=["videos"],
    response_class=Response,
    responses={200: {"content": {"application/vnd.apple.mpegurl": {}, "video/mp4": {}}}},
)
async def media_file(video_id: uuid.UUID, path: str, scope: OrgDep) -> Response:
    data, ctype = await videos.read_media(scope.ctx, video_id, path)
    cache = "private, max-age=60" if path.endswith(".m3u8") else "private, max-age=86400, immutable"
    return Response(data, media_type=ctype, headers={"cache-control": cache})


@router.post("/videos/{video_id}/media-token", tags=["videos"])
async def media_token(video_id: uuid.UUID, scope: OrgDep) -> dict[str, object]:
    """Signed media path for the native apps' players (HLS segments without auth headers)."""
    return await videos.media_token(scope.ctx, video_id)


@router.get("/videos/{video_id}/analysis", response_model=AnalysisOut, tags=["analysis"])
async def get_analysis(video_id: uuid.UUID, scope: OrgDep) -> dict[str, object]:
    return await videos.analysis(scope.ctx, video_id)


@router.get(
    "/videos/{video_id}/tracks/{n}",
    tags=["analysis"],
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
)
async def track_chunk(video_id: uuid.UUID, n: int, scope: OrgDep) -> Response:
    """30 s of positions as little-endian float32 rows [t_ms, track, x, y]."""
    data = await videos.read_track_chunk(scope.ctx, video_id, n)
    return Response(
        data,
        media_type="application/octet-stream",
        headers={"cache-control": "private, max-age=3600"},
    )


@router.put(
    "/videos/{video_id}/tracks/{track_no}/identity", response_model=TrackOut, tags=["analysis"]
)
async def set_track_identity(
    video_id: uuid.UUID, track_no: int, data: TrackIdentity, scope: OrgDep
) -> Track:
    """Assign a roster player (or just a jersey number) to a track; null clears it."""
    return await videos.set_track_identity(
        scope.ctx, video_id, track_no, data.player_id, data.number
    )


@router.get("/matches/{match_id}/physical", response_model=dict[str, Any], tags=["analysis"])
async def match_physical(match_id: uuid.UUID, scope: OrgDep) -> dict[str, object]:
    """Distance, speed bands, sprints and heatmap per player (estimated from video tracking)."""
    return await videos.match_physical(scope.ctx, match_id)


@router.post("/videos/{video_id}/calibration", status_code=202, tags=["analysis"])
async def calibrate(video_id: uuid.UUID, data: CalibrationIn, scope: OrgDep) -> dict[str, str]:
    points = [
        {"image": list(p.image), "court": list(p.court), "height_m": p.height_m}
        for p in data.points
    ]
    job = await videos.calibrate_manually(scope.ctx, video_id, points, data.space, data.frame_ms)
    return {"job_id": str(job.id)}


@router.get(
    "/videos/{video_id}/panorama",
    tags=["analysis"],
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}},
)
async def panorama(video_id: uuid.UUID, scope: OrgDep) -> Response:
    """Hall image of the last analysis (panorama or median frame) to mark the court on."""
    data = await videos.read_panorama(scope.ctx, video_id)
    return Response(
        data, media_type="image/jpeg", headers={"cache-control": "private, max-age=300"}
    )


# ---- live job progress (SSE) ---------------------------------------------------------------


@router.get(
    "/matches/{match_id}/stream",
    tags=["matches"],
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def match_stream(
    request: Request, org_id: Annotated[uuid.UUID, Path()], match_id: uuid.UUID
) -> StreamingResponse:
    """Server-Sent Events with job progress. Authorises in a short transaction, then holds no
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
        await service.get_match(ctx, match_id)
        jobs = (
            await db.scalars(
                select(ProcessingJob)
                .where(ProcessingJob.match_id == match_id)
                .order_by(ProcessingJob.created_at.desc())
                .limit(10)
            )
        ).all()
        snapshot = [videos.job_event(j) for j in jobs]
    bus = app.state.events

    async def stream() -> AsyncIterator[str]:
        yield f"event: snapshot\ndata: {json.dumps(snapshot, default=str)}\n\n"
        events = bus.subscribe(f"match:{match_id}")
        nxt: asyncio.Task[Any] | None = None
        try:
            while not await request.is_disconnected():
                nxt = nxt or asyncio.ensure_future(anext(events))
                done, _ = await asyncio.wait({nxt}, timeout=15)
                if done:
                    yield f"event: job\ndata: {json.dumps(nxt.result(), default=str)}\n\n"
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


# ---- clips, playlists ----------------------------------------------------------------------


@router.get("/matches/{match_id}/clips", response_model=list[ClipOut], tags=["clips"])
async def list_clips(match_id: uuid.UUID, scope: OrgDep) -> list[Clip]:
    return await media.list_clips(scope.ctx, match_id)


@router.post("/clips", response_model=ClipOut, status_code=201, tags=["clips"])
async def create_clip(data: ClipCreate, scope: OrgDep) -> Clip:
    return await media.create_clip(scope.ctx, data)


@router.delete("/clips/{clip_id}", status_code=204, tags=["clips"])
async def delete_clip(clip_id: uuid.UUID, scope: OrgDep) -> None:
    await media.delete_clip(scope.ctx, clip_id)


@router.get("/teams/{team_id}/playlists", response_model=list[PlaylistOut], tags=["playlists"])
async def list_playlists(team_id: uuid.UUID, scope: OrgDep) -> list[PlaylistOut]:
    return await media.list_playlists(scope.ctx, team_id)


@router.post(
    "/teams/{team_id}/playlists", response_model=PlaylistDetail, status_code=201, tags=["playlists"]
)
async def create_playlist(
    team_id: uuid.UUID, data: PlaylistCreate, scope: OrgDep
) -> PlaylistDetail:
    pl: Playlist = await media.create_playlist(scope.ctx, team_id, data)
    return await media.playlist_detail(scope.ctx, pl.id)


@router.get("/playlists/{playlist_id}", response_model=PlaylistDetail, tags=["playlists"])
async def get_playlist(playlist_id: uuid.UUID, scope: OrgDep) -> PlaylistDetail:
    return await media.playlist_detail(scope.ctx, playlist_id)


@router.patch("/playlists/{playlist_id}", response_model=PlaylistDetail, tags=["playlists"])
async def update_playlist(
    playlist_id: uuid.UUID, data: PlaylistUpdate, scope: OrgDep
) -> PlaylistDetail:
    await media.update_playlist(scope.ctx, playlist_id, data)
    return await media.playlist_detail(scope.ctx, playlist_id)


@router.delete("/playlists/{playlist_id}", status_code=204, tags=["playlists"])
async def delete_playlist(playlist_id: uuid.UUID, scope: OrgDep) -> None:
    await media.delete_playlist(scope.ctx, playlist_id)


@router.post(
    "/playlists/{playlist_id}/items",
    response_model=PlaylistDetail,
    status_code=201,
    tags=["playlists"],
)
async def add_item(
    playlist_id: uuid.UUID, data: PlaylistItemCreate, scope: OrgDep
) -> PlaylistDetail:
    await media.add_item(scope.ctx, playlist_id, data)
    return await media.playlist_detail(scope.ctx, playlist_id)


@router.delete("/playlists/{playlist_id}/items/{item_id}", status_code=204, tags=["playlists"])
async def remove_item(playlist_id: uuid.UUID, item_id: uuid.UUID, scope: OrgDep) -> None:
    await media.remove_item(scope.ctx, playlist_id, item_id)


@router.put("/playlists/{playlist_id}/order", response_model=PlaylistDetail, tags=["playlists"])
async def reorder(playlist_id: uuid.UUID, data: ReorderIn, scope: OrgDep) -> PlaylistDetail:
    await media.reorder(scope.ctx, playlist_id, data.item_ids)
    return await media.playlist_detail(scope.ctx, playlist_id)


# ---- comments, drawings --------------------------------------------------------------------


@router.get("/matches/{match_id}/comments", response_model=list[CommentOut], tags=["comments"])
async def list_comments(match_id: uuid.UUID, scope: OrgDep) -> list[CommentOut]:
    return await media.list_comments(scope.ctx, match_id)


@router.post(
    "/matches/{match_id}/comments", response_model=CommentOut, status_code=201, tags=["comments"]
)
async def add_comment(match_id: uuid.UUID, data: CommentCreate, scope: OrgDep) -> CommentOut:
    c = await media.add_comment(scope.ctx, match_id, data)
    return CommentOut(
        id=c.id,
        t_ms=c.t_ms,
        body=c.body,
        author_id=c.author_id,
        author_name=scope.user.name,
        created_at=c.created_at,
        can_delete=True,
    )


@router.delete("/comments/{comment_id}", status_code=204, tags=["comments"])
async def delete_comment(comment_id: uuid.UUID, scope: OrgDep) -> None:
    await media.delete_comment(scope.ctx, comment_id)


@router.get(
    "/matches/{match_id}/annotations", response_model=list[AnnotationOut], tags=["annotations"]
)
async def list_annotations(match_id: uuid.UUID, scope: OrgDep) -> list[Annotation]:
    return await media.list_annotations(scope.ctx, match_id)


@router.post(
    "/matches/{match_id}/annotations",
    response_model=AnnotationOut,
    status_code=201,
    tags=["annotations"],
)
async def add_annotation(match_id: uuid.UUID, data: AnnotationCreate, scope: OrgDep) -> Annotation:
    return await media.add_annotation(scope.ctx, match_id, data)


@router.delete("/annotations/{annotation_id}", status_code=204, tags=["annotations"])
async def delete_annotation(annotation_id: uuid.UUID, scope: OrgDep) -> None:
    await media.delete_annotation(scope.ctx, annotation_id)


public_media = APIRouter(prefix="/v1/media", tags=["videos"])


@public_media.get(
    "/{video_id}/{token}/{path:path}",
    response_class=Response,
    responses={200: {"content": {"application/vnd.apple.mpegurl": {}, "video/mp4": {}}}},
)
async def signed_media(video_id: uuid.UUID, token: str, path: str, ctx: CtxDep) -> Response:
    data, ctype = await videos.read_signed_media(ctx, video_id, token, path)
    return Response(data, media_type=ctype, headers={"cache-control": "private, max-age=600"})

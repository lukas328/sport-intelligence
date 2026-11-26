"""Videos of a match: upload, link import, jobs, media, analysis and tracks.

The work lives in sibling modules: `video_uploads` (direct multipart to storage, deleting a file,
the match status from its files), `video_jobs` (ingest, camera sync, job budgets),
`video_callbacks` (worker callbacks, handled per job kind), `video_media` (storage paths, media
reads, signed links), `video_analysis` (the analysis, its result and the court) and `video_tracks`
(identities, physical load); `video_base` holds what they share. The link import stays here (tests
replace the URL check in this module); every name callers use is importable from here.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import PurePosixPath

from handball_api.core.errors import ProblemError
from handball_api.core.net import UnsafeUrlError, check_public_https_url
from handball_api.models import VideoAsset
from handball_api.models.enums import VideoStatus
from handball_api.schemas.matches import LinkImport
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.matches import get_match
from handball_api.services.policies import Action
from handball_api.services.video_analysis import (
    _apply_analysis_result,
    _earlier_part_busy,
    _enqueue_analysis,
    _part_of,
    _rosters,
    _with_sure,
    analysis,
    calibrate_manually,
    calibration_origin,
    calibration_state,
    calibration_suggestion,
    confirm_calibration,
    court_from_part,
    court_points_for,
    read_panorama,
    read_track_chunk,
    read_view_chunk,
    retry_analysis,
    start_analysis,
    start_waiting,
)
from handball_api.services.video_base import (
    ANALYSIS_FUNC,
    CLICKED,
    IMPORT_FUNC,
    INGEST_FUNC,
    LINE_CLICKS,
    PENDING,
    PIPELINE_VERSION,
    SYNC_FUNC,
    SYNC_MIN_CONFIDENCE,
    UNDETERMINABLE,
    VIDEO_EXT,
    WAITING,
    get_asset,
)
from handball_api.services.video_callbacks import (
    ON_FAILED,
    ON_SUCCEEDED,
    THREE_THINGS_MIN_GOALS,
    Failed,
    Succeeded,
    _analysis_failed,
    _analysis_succeeded,
    _file_failed,
    _import_succeeded,
    _ingest_succeeded,
    _ready_note,
    _sync_failed,
    _sync_succeeded,
    _tell_staff,
    apply_job_update,
)
from handball_api.services.video_jobs import (
    _apply_ingest_result,
    _apply_sync_result,
    _elapsed_seconds,
    _job_payload,
    _new_job,
    _same_file,
    _sync_after_ingest,
    job_budget_s,
    job_event,
    reprocess,
    set_offset,
    start_ingest,
    start_sync,
)
from handball_api.services.video_media import (
    MEDIA_PATH,
    MEDIA_TOKEN_S,
    MEDIA_TYPES,
    _media_sig,
    _same_route,
    media_prefix,
    media_prefix_of,
    media_token,
    read_media,
    read_media_object,
    read_signed_media,
)
from handball_api.services.video_tracks import (
    BANDS,
    _merge_physical,
    match_physical,
    set_track_identity,
)
from handball_api.services.video_uploads import (
    _key,
    _uploading,
    _whole_match,
    abort_upload,
    complete_upload,
    create_upload,
    list_parts,
    presign_parts,
    settle_status,
)

__all__ = [
    "ANALYSIS_FUNC",
    "BANDS",
    "CLICKED",
    "IMPORT_FUNC",
    "INGEST_FUNC",
    "LINE_CLICKS",
    "MEDIA_PATH",
    "MEDIA_TOKEN_S",
    "MEDIA_TYPES",
    "ON_FAILED",
    "ON_SUCCEEDED",
    "PENDING",
    "PIPELINE_VERSION",
    "SYNC_FUNC",
    "SYNC_MIN_CONFIDENCE",
    "THREE_THINGS_MIN_GOALS",
    "UNDETERMINABLE",
    "VIDEO_EXT",
    "WAITING",
    "Failed",
    "Succeeded",
    "_analysis_failed",
    "_analysis_succeeded",
    "_apply_analysis_result",
    "_apply_ingest_result",
    "_apply_sync_result",
    "_earlier_part_busy",
    "_elapsed_seconds",
    "_enqueue_analysis",
    "_file_failed",
    "_import_succeeded",
    "_ingest_succeeded",
    "_job_payload",
    "_key",
    "_media_sig",
    "_merge_physical",
    "_new_job",
    "_part_of",
    "_ready_note",
    "_rosters",
    "_same_file",
    "_same_route",
    "_sync_after_ingest",
    "_sync_failed",
    "_sync_succeeded",
    "_tell_staff",
    "_uploading",
    "_whole_match",
    "_with_sure",
    "abort_upload",
    "analysis",
    "apply_job_update",
    "calibrate_manually",
    "calibration_origin",
    "calibration_state",
    "calibration_suggestion",
    "complete_upload",
    "confirm_calibration",
    "court_from_part",
    "court_points_for",
    "create_upload",
    "get_asset",
    "import_link",
    "job_budget_s",
    "job_event",
    "list_parts",
    "match_physical",
    "media_prefix",
    "media_prefix_of",
    "media_token",
    "presign_parts",
    "read_media",
    "read_media_object",
    "read_panorama",
    "read_signed_media",
    "read_track_chunk",
    "read_view_chunk",
    "reprocess",
    "retry_analysis",
    "set_offset",
    "set_track_identity",
    "settle_status",
    "start_analysis",
    "start_ingest",
    "start_sync",
    "start_waiting",
]


async def import_link(ctx: Ctx, match_id: uuid.UUID, data: LinkImport) -> VideoAsset:
    match = await get_match(ctx, match_id, Action.VIDEO_UPLOAD)
    url = str(data.url)
    try:
        await asyncio.to_thread(check_public_https_url, url)  # DNS lookup blocks
    except UnsafeUrlError as exc:
        raise ProblemError(422, "unsafe-url", str(exc)) from exc
    asset_id = uuid.uuid4()
    name = PurePosixPath(url.split("?")[0]).name or "video.mp4"
    if not VIDEO_EXT.search(name):
        name = f"{name}.mp4"
    asset = VideoAsset(
        id=asset_id,
        organization_id=match.organization_id,
        match_id=match.id,
        role=data.role,
        status=VideoStatus.UPLOADING,
        filename=name[:255],
        content_type="video/mp4",
        size_bytes=0,
        storage_key=_key(match, asset_id, name),
        part_size=ctx.settings.upload_part_size,
        source_url=url,
        uploaded_by_id=ctx.user_id,
    )
    ctx.db.add(asset)
    await ctx.db.flush()
    job = await _new_job(ctx, asset, "import")
    await ctx.enqueue("pipeline", IMPORT_FUNC, str(job.id), _job_payload(ctx, asset, job, url=url))
    await audit.record(
        ctx, "video.import_started", target_type="video", target_id=asset.id, data={"url": url}
    )
    return asset

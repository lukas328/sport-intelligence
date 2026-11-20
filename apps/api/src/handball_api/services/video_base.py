"""Settings shared by the video modules (services/videos.py) and the asset lookup."""

from __future__ import annotations

import re
import uuid

from handball_api.core.errors import ProblemError
from handball_api.models import VideoAsset
from handball_api.services import checks
from handball_api.services.context import Ctx
from handball_api.services.matches import get_match
from handball_api.services.policies import Action

PIPELINE_VERSION = "0.2.0"
# keys of VideoAsset.analysis: the court points the coach clicked (of the last run that succeeded
# with them, reused by every later run) and those of a run still going
CLICKED, PENDING = "court_points", "court_points_pending"
UNDETERMINABLE = checks.UNDETERMINABLE  # the coach said the court cannot be set on this video
LINE_CLICKS = (
    "court_clicks"  # the coach's latest line clicks (services/court_clicks), to edit again
)
INGEST_FUNC = "handball_worker.ingest.run_ingest"
ANALYSIS_FUNC = "handball_gpu_worker.analysis.run_analysis"
SYNC_FUNC = "handball_gpu_worker.sync.run_sync"
SYNC_MIN_CONFIDENCE = 0.35
IMPORT_FUNC = "handball_worker.ingest.run_import"
WAITING = "waiting_job"  # analysis meta: the job of this part waits for an earlier part's analysis
VIDEO_EXT = re.compile(r"\.(mp4|mov|m4v|mkv|avi|mts|m2ts|webm)$", re.IGNORECASE)


async def get_asset(
    ctx: Ctx, asset_id: uuid.UUID, action: Action = Action.MATCH_READ
) -> VideoAsset:
    asset = await ctx.db.get(VideoAsset, asset_id)
    if asset is None:
        raise ProblemError(404, "not-found", "Video not found")
    await get_match(ctx, asset.match_id, action)
    return asset

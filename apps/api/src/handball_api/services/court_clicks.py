"""The court from clicked lines (manual calibration, line mode).

The coach chooses a court line in the calibration dialog and clicks two or three points on it,
on the hall image ("panorama") or on one video frame ("frame" at `frame_ms`); named points
(corners, post feet) may be added. `handball_court.clicks` fits the court to the clicks and
refuses clicks that do not agree with one court, within about a second, so the dialog can show
the court over the image before anything is stored.

Submitting stores the court the usual way (`videos.calibrate_manually`): the fitted court is
turned into point pairs (where the coach clicked and the visible court around it), the analysis
runs again with them (source "user_correction"), and the court is offered to later videos of
the same hall (`halls`). The GPU worker sees ordinary clicked points.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import numpy as np

from handball_api.core.errors import ProblemError
from handball_api.models import ProcessingJob, VideoAsset
from handball_api.models.enums import VideoStatus
from handball_api.services import audit, videos
from handball_api.services.context import Ctx
from handball_api.services.policies import Action
from handball_court.clicks import ClicksError, ClicksFit, court_model, fit_clicks

Px = tuple[float, float]

CLICKS = videos.LINE_CLICKS  # analysis meta: the coach's latest line clicks, to edit again
MAX_PAIRS = 40  # as many point pairs as the points dialog may send
GRID_M = 2.5  # court points offered around the clicks
FRAME_SIZE = (1280, 720)  # the proxy frame when the video does not say

_CODES = {"unknown": "clicks-unknown", "too_few": "clicks-too-few", "disagree": "clicks-disagree"}


def model() -> dict[str, Any]:
    """The clickable court: lines as polylines and named points, in court metres."""
    return court_model()


def image_size(asset: VideoAsset, space: str) -> tuple[int, int]:
    if space == "panorama":
        pano = (asset.analysis or {}).get("panorama")
        if not isinstance(pano, dict) or not pano.get("width"):
            raise ProblemError(409, "no-hall-image", "Run the analysis first to get the hall image")
        return int(pano["width"]), int(pano["height"])
    if asset.width and asset.height:
        return int(asset.width), int(asset.height)
    return FRAME_SIZE


async def fit(
    points: dict[str, Px], lines: dict[str, list[Px]], size: tuple[int, int]
) -> ClicksFit:
    """The court through the clicks (off the event loop: about a second of CPU)."""
    try:
        return await asyncio.to_thread(fit_clicks, points, lines, size)
    except ClicksError as exc:
        raise ProblemError(422, _CODES.get(exc.code, "clicks-disagree"), str(exc)) from exc


def out(found: ClicksFit, size: tuple[int, int]) -> dict[str, Any]:
    return {
        "homography": np.round(found.homography, 9).tolist(),
        "image_size": list(size),
        "residual_px": {"median": round(found.median_px, 2), "max": round(found.max_px, 2)},
        "dropped": [
            {"kind": d.kind, "name": d.name, "index": None if d.index < 0 else d.index}
            for d in found.dropped
        ],
    }


def point_pairs(
    found: ClicksFit,
    points: dict[str, Px],
    lines: dict[str, list[Px]],
    size: tuple[int, int],
) -> list[dict[str, Any]]:
    """Image/court pairs that carry the fitted court to the worker: the court positions of the
    clicks the fit kept, then court grid points inside the image, at most MAX_PAIRS. Pairs taken
    from one homography give that homography back exactly."""
    h = found.homography
    inv = np.linalg.inv(h)
    dropped = {(d.kind, d.name, d.index) for d in found.dropped}
    clicked = [p for n, p in points.items() if ("point", n, -1) not in dropped]
    clicked += [
        p for n, c in lines.items() for j, p in enumerate(c) if ("line", n, j) not in dropped
    ]
    court: list[tuple[float, float]] = []
    if clicked:
        q = np.c_[np.array(clicked, np.float64), np.ones(len(clicked))] @ inv.T
        court += [(float(x / w), float(y / w)) for x, y, w in q if w > 0]
    w_px, h_px = size
    grid = [
        (x, y)
        for x in np.arange(0.0, 40.0 + 1e-9, GRID_M)
        for y in np.arange(0.0, 20.0 + 1e-9, GRID_M)
    ]
    g = np.c_[np.array(grid), np.ones(len(grid))] @ h.T
    inside = [
        (float(x), float(y))
        for (x, y), (u, v, w) in zip(grid, g, strict=True)
        if w > 0 and 0 <= u / w <= w_px and 0 <= v / w <= h_px
    ]
    # keep the clicks' own places, fill with the grid evenly
    room = max(0, MAX_PAIRS - min(len(court), MAX_PAIRS // 2))
    step = max(1, -(-len(inside) // room)) if room else len(inside) + 1
    court = court[: MAX_PAIRS // 2] + inside[::step]
    court = [(x, y) for x, y in court if -5 <= x <= 45 and -5 <= y <= 25][:MAX_PAIRS]
    img = np.c_[np.array(court), np.ones(len(court))] @ h.T
    return [
        {"image": [round(u / w, 2), round(v / w, 2)], "court": [round(x, 3), round(y, 3)]}
        for (x, y), (u, v, w) in zip(court, img, strict=True)
    ]


async def _asset(ctx: Ctx, asset_id: uuid.UUID, space: str) -> tuple[VideoAsset, tuple[int, int]]:
    asset = await videos.get_asset(ctx, asset_id, Action.VIDEO_UPLOAD)
    if asset.status != VideoStatus.READY or not asset.proxy_key:
        raise ProblemError(409, "video-not-ready", "The video is still being processed")
    return asset, image_size(asset, space)


async def check(
    ctx: Ctx,
    asset_id: uuid.UUID,
    points: dict[str, Px],
    lines: dict[str, list[Px]],
    space: str,
) -> dict[str, Any]:
    """The court through the clicks, nothing stored (for the dialog's overlay)."""
    _, size = await _asset(ctx, asset_id, space)
    return out(await fit(points, lines, size), size)


async def submit(
    ctx: Ctx,
    asset_id: uuid.UUID,
    points: dict[str, Px],
    lines: dict[str, list[Px]],
    space: str,
    frame_ms: int,
) -> tuple[ProcessingJob, dict[str, Any]]:
    """Check the clicks, store the court as the coach's and run the analysis again with it."""
    asset, size = await _asset(ctx, asset_id, space)
    found = await fit(points, lines, size)
    pairs = point_pairs(found, points, lines, size)
    if len(pairs) < 4:
        raise ProblemError(422, "clicks-disagree", "The clicked court is not in the image")
    asset.analysis = {
        **(asset.analysis or {}),
        CLICKS: {
            "space": space,
            "frame_ms": frame_ms,
            "points": {n: list(p) for n, p in points.items()},
            "lines": {n: [list(p) for p in c] for n, c in lines.items()},
        },
    }
    await audit.record(
        ctx,
        "video.court_clicked",
        target_type="video",
        target_id=asset.id,
        data={
            "lines": len(lines),
            "points": len(points),
            "median_px": round(found.median_px, 2),
            "dropped": len(found.dropped),
        },
    )
    job = await videos.calibrate_manually(ctx, asset.id, pairs, space, frame_ms)
    return job, out(found, size)

"""The hall of a match, and the courts already marked in it (backlog item 1, ADR 025).

Most club videos come from a camera that stands at the same place in the home hall every week.
Once a coach has clicked (or confirmed) the court on one video, the analysis of every later video
of that hall tries the earlier court first: the worker matches the two hall images and carries
the court over (`handball_vision.hallmatch`), and only falls back to the automatic court or the
click dialog when the camera stood elsewhere.

The hall is the match's venue, which the official game data fills in (handball.ch `venueName`,
`services/official.py`); a match without a venue that is a home game gets the team's usual home
hall as a suggestion.
"""

from __future__ import annotations

import unicodedata
from collections import Counter
from typing import Any, Literal

from sqlalchemy import select

from handball_api.models import CameraCalibration, Match, VideoAsset
from handball_api.services.context import Ctx

MAX_REFERENCES = 3  # earlier videos the worker tries (the newest first)
HallSource = Literal["official", "match", "home_matches"]


def fold(name: str | None) -> str:
    """Hall names compared without case, accents and repeated spaces."""
    s = unicodedata.normalize("NFKD", (name or "").replace("ß", "ss"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return " ".join(s.split())


async def hall_of(ctx: Ctx, match: Match) -> tuple[str | None, HallSource | None]:
    """The match's hall and where the name comes from: the official game data, the match as
    entered, or (a home game without a venue) the venue of most of the team's home games."""
    if match.venue:
        return match.venue, "official" if match.official_game_id is not None else "match"
    if not match.is_home:
        return None, None
    venues = (
        await ctx.db.scalars(
            select(Match.venue).where(
                Match.team_id == match.team_id,
                Match.is_home.is_(True),
                Match.venue.is_not(None),
                Match.id != match.id,
            )
        )
    ).all()
    counts = Counter(fold(v) for v in venues if v)
    if not counts:
        return None, None
    best = counts.most_common(1)[0][0]
    return next(v for v in venues if v and fold(v) == best), "home_matches"


async def references(
    ctx: Ctx, asset: VideoAsset, hall: str | None, limit: int = MAX_REFERENCES
) -> list[dict[str, Any]]:
    """Earlier videos of the organisation in the same hall whose current court a person clicked
    or confirmed, newest first: what the worker needs to carry the court over (the hall image key
    and the court homography in that image)."""
    from handball_api.services.videos import media_prefix

    key = fold(hall)
    if not key:
        return []
    rows = await ctx.db.execute(
        select(CameraCalibration, VideoAsset, Match.venue)
        .join(VideoAsset, VideoAsset.id == CameraCalibration.video_asset_id)
        .join(Match, Match.id == VideoAsset.match_id)
        .where(
            CameraCalibration.organization_id == asset.organization_id,
            VideoAsset.id != asset.id,
        )
        .order_by(CameraCalibration.created_at.desc())
    )
    seen: set[Any] = set()
    out: list[dict[str, Any]] = []
    for cal, video, venue in rows.all():
        if video.id in seen:
            continue
        seen.add(video.id)  # the newest court of a video is its court
        if cal.source != "user_correction" or fold(venue) != key:
            continue
        pano = (video.analysis or {}).get("panorama")
        # the court must be on that video's hall image (not on a single frame of it)
        if not isinstance(pano, dict) or [pano.get("width"), pano.get("height")] != list(
            cal.image_size
        ):
            continue
        out.append(
            {
                "video_id": str(video.id),
                "panorama_key": f"{media_prefix(video)}analysis/panorama.jpg",
                "homography": cal.homography,
                "image_size": list(cal.image_size),
                "hall": venue,
            }
        )
        if len(out) >= limit:
            break
    return out


async def summary(ctx: Ctx, asset: VideoAsset, match: Match) -> dict[str, Any]:
    """What the analysis view shows about the hall: its name, where the name comes from and how
    many earlier videos of it have a court to carry over."""
    name, source = await hall_of(ctx, match)
    refs = await references(ctx, asset, name, limit=50) if name else []
    return {"name": name, "source": source, "calibrated_videos": len(refs)}

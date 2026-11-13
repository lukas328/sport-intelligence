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
from sqlalchemy.orm import aliased

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
            select(Match.venue)
            .where(
                Match.team_id == match.team_id,
                Match.is_home.is_(True),
                Match.venue.is_not(None),
                Match.id != match.id,
            )
            # a fixed order: the hall and its spelling must not depend on the database's row order
            .order_by(Match.created_at, Match.id)
        )
    ).all()
    counts = Counter(fold(v) for v in venues if v)
    if not counts:
        return None, None
    best = counts.most_common(1)[0][0]
    # the most used spelling of that hall; on a tie the one entered first (Counter keeps order)
    spellings = Counter(v for v in venues if v and fold(v) == best)
    return spellings.most_common(1)[0][0], "home_matches"


async def match_references(ctx: Ctx, asset: VideoAsset, only: Any = None) -> list[dict[str, Any]]:
    """The other files of the same match (its other half) whose court a person clicked or
    confirmed: tried first, whatever the hall is called (Q-VIDEO-PARTS). `only`: one file."""
    return await _references(ctx, asset, None, MAX_REFERENCES, same_match=True, only=only)


async def references(
    ctx: Ctx, asset: VideoAsset, hall: str | None, limit: int = MAX_REFERENCES
) -> list[dict[str, Any]]:
    return await _references(ctx, asset, hall, limit)


async def _references(
    ctx: Ctx,
    asset: VideoAsset,
    hall: str | None,
    limit: int,
    same_match: bool = False,
    only: Any = None,
) -> list[dict[str, Any]]:
    """Earlier videos of the organisation in the same hall whose current court a person clicked
    or confirmed, newest first: what the worker needs to carry the court over (the hall image key
    and the court homography in that image)."""
    from handball_api.services.videos import media_prefix_of

    key = fold(hall)
    if not key and not same_match:
        return []
    # the newest court of each video is its court: one row per video from the database, with
    # only the columns needed (the hall image size, not the whole analysis)
    latest = (
        select(CameraCalibration)
        .join(VideoAsset, VideoAsset.id == CameraCalibration.video_asset_id)
        .where(
            CameraCalibration.organization_id == asset.organization_id,
            VideoAsset.id != asset.id,
        )
        .distinct(CameraCalibration.video_asset_id)
        .order_by(CameraCalibration.video_asset_id, CameraCalibration.created_at.desc())
        .subquery()
    )
    cal = aliased(CameraCalibration, latest)
    pano = VideoAsset.analysis["panorama"]
    rows = await ctx.db.execute(
        select(
            VideoAsset.id,
            VideoAsset.match_id,
            Match.venue,
            cal.homography,
            cal.image_size,
            pano["width"],
            pano["height"],
        )
        .join(VideoAsset, VideoAsset.id == cal.video_asset_id)
        .join(Match, Match.id == VideoAsset.match_id)
        .where(
            cal.source == "user_correction",
            VideoAsset.match_id == asset.match_id if same_match else Match.venue.is_not(None),
            *([VideoAsset.id == only] if only is not None else []),
        )
        .order_by(cal.created_at.desc())
    )
    out: list[dict[str, Any]] = []
    for video_id, match_id, venue, homography, image_size, width, height in rows.all():
        if not same_match and fold(venue) != key:
            continue
        # the court must be on that video's hall image (not on a single frame of it)
        if [width, height] != list(image_size):
            continue
        out.append(
            {
                "video_id": str(video_id),
                "panorama_key": f"{media_prefix_of(asset.organization_id, match_id, video_id)}"
                "analysis/panorama.jpg",
                "homography": homography,
                "image_size": list(image_size),
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
    # the team's usual home hall is a guess for carrying a court over (the hall images are
    # compared before anything is taken), not a name to show (real-video test E11)
    if source == "home_matches":
        name, source = None, None
    refs = await references(ctx, asset, name, limit=50) if name else []
    return {"name": name, "source": source, "calibrated_videos": len(refs)}

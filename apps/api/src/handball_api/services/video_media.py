"""Media of a video: storage paths, reading HLS files and posters, signed media links
for the native apps (5.5)."""

from __future__ import annotations

import hashlib
import hmac
import posixpath
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from handball_api.core.db import set_tenant, system_access
from handball_api.core.errors import ProblemError
from handball_api.core.storage import ObjectNotFoundError
from handball_api.models import VideoAsset
from handball_api.services import feed, timeline
from handball_api.services.context import Ctx
from handball_api.services.video_base import get_asset

MEDIA_PATH = re.compile(r"^[A-Za-z0-9_\-]+(/[A-Za-z0-9_\-]+)*\.(m3u8|m4s|mp4|ts|jpg|vtt)$")
MEDIA_TYPES = {
    "m3u8": "application/vnd.apple.mpegurl",
    "m4s": "video/iso.segment",
    "mp4": "video/mp4",
    "ts": "video/mp2t",
    "jpg": "image/jpeg",
    "vtt": "text/vtt",
}


# HLS media segments and init segments: what a playlist may point straight to storage for
SEGMENT_PATH = re.compile(r"\.(m4s|mp4|ts)$")
# a segment never changes under its key (a reprocess writes a new folder)
SEGMENT_CACHE = "private, max-age=86400, immutable"
_MAP_URI = re.compile(r'URI="([^"]+)"')


def media_prefix(asset: VideoAsset) -> str:
    return media_prefix_of(asset.organization_id, asset.match_id, asset.id)


def media_prefix_of(org_id: uuid.UUID, match_id: uuid.UUID, video_id: uuid.UUID) -> str:
    return f"{org_id}/{match_id}/{video_id}/"


async def read_media(ctx: Ctx, asset_id: uuid.UUID, path: str) -> tuple[bytes, str]:
    try:
        asset = await get_asset(ctx, asset_id)
    except ProblemError:
        # parents: the match video of a match in which their child has scenes (4.7, 4.9)
        guest = await ctx.db.get(VideoAsset, asset_id)
        if guest is None or not await feed.guardian_sees_match(ctx, guest.match_id):
            raise
        asset = guest
    return await read_media_object(ctx, asset, path)


def _same_route(other: VideoAsset) -> str:
    return f"{other.id}/media/"


def _servable(path: str) -> bool:
    """Player media a browser may get: never originals or the analysis proxy."""
    return (
        bool(MEDIA_PATH.match(path))
        and ".." not in path
        and path != "proxy.mp4"
        and not path.startswith("original")
    )


def rewrite_playlist(text: str, urls: dict[str, str]) -> str:
    """The playlist with the URIs of `urls` replaced (segment lines and `#EXT-X-MAP` URIs)."""
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#EXT-X-MAP:"):
            m = _MAP_URI.search(line)
            if m and m.group(1) in urls:
                line = line.replace(m.group(0), f'URI="{urls[m.group(1)]}"')
        elif line and not line.startswith("#"):
            line = urls.get(line, line)
        out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def playlist_segments(text: str) -> list[str]:
    """The relative URIs of the media and init segments of a playlist (not other playlists)."""
    uris = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#EXT-X-MAP:"):
            m = _MAP_URI.search(line)
            uri = m.group(1) if m else ""
        elif line and not line.startswith("#"):
            uri = line
        else:
            continue
        if uri and "://" not in uri and not uri.startswith("/") and SEGMENT_PATH.search(uri):
            uris.append(uri)
    return uris


def direct_playlist(ctx: Ctx, part: VideoAsset, path: str, data: bytes) -> bytes:
    """A playlist of `part` (at `path` in its media folder) whose segments point to presigned
    storage URLs, so the bytes go from storage to the player without the API (ADR 002 point 7).
    Only files of the part's own media folder are signed, never originals or the proxy."""
    text = data.decode()
    base = posixpath.dirname(path)
    keys: dict[str, str] = {}
    for uri in playlist_segments(text):
        rel = posixpath.normpath(posixpath.join(base, uri))
        if _servable(rel):
            keys[uri] = media_prefix(part) + rel
    if not keys:
        return data
    signed = ctx.storage.presign_gets(
        ctx.settings.s3_bucket_videos,
        list(keys.values()),
        ctx.settings.media_direct_ttl_s,
        SEGMENT_CACHE,
    )
    return rewrite_playlist(text, dict(zip(keys, signed, strict=True))).encode()


async def read_media_object(
    ctx: Ctx, asset: VideoAsset, path: str, sibling: Any = _same_route
) -> tuple[bytes, str]:
    """One file of a video's player media (HLS, poster, thumbnails) and its content type, for a
    caller that has already checked access. Originals and the analysis proxy are never served.
    A missing object is a 404; any other storage error propagates (a 500 the alerting sees, not a
    silent 404). The first part of a match with several parts serves playlists and previews over
    all parts (`sibling(part)`: the URL path from the videos folder to that part's media)."""
    if not _servable(path):
        raise ProblemError(404, "not-found", "Not found")
    # with direct media, the segments of every playlist point straight to storage; the access
    # check above and in the callers stays the same, only the bytes take another way
    direct = ctx.settings.media_direct and path.endswith(".m3u8")

    async def read(part: VideoAsset, p: str) -> bytes | None:
        try:
            data, _ = await ctx.storage.get(ctx.settings.s3_bucket_videos, media_prefix(part) + p)
        except ObjectNotFoundError:
            return None
        if direct and p.endswith(".m3u8"):
            return direct_playlist(ctx, part, p, bytes(data))
        return bytes(data)

    joined = await timeline.joined_playlist(ctx, asset, path, read, sibling)
    if joined is not None:
        return joined, MEDIA_TYPES[path.rsplit(".", 1)[1]]
    try:
        data, _ = await ctx.storage.get(ctx.settings.s3_bucket_videos, media_prefix(asset) + path)
    except ObjectNotFoundError as exc:
        raise ProblemError(404, "not-found", "Not found") from exc
    if direct:
        data = direct_playlist(ctx, asset, path, bytes(data))
    return data, MEDIA_TYPES[path.rsplit(".", 1)[1]]


MEDIA_TOKEN_S = 4 * 3600


def _media_sig(ctx: Ctx, asset_id: uuid.UUID, exp: int) -> str:
    key = ctx.settings.secret_key.get_secret_value().encode()
    return hmac.new(key, f"media:{asset_id}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]


async def media_token(ctx: Ctx, asset_id: uuid.UUID) -> dict[str, object]:
    """A path token for players that cannot send auth headers to HLS segments (native apps).
    Issued only to someone who may watch the video; valid for four hours."""
    asset = await get_asset(ctx, asset_id)
    exp = int(datetime.now(UTC).timestamp()) + MEDIA_TOKEN_S
    token = f"{exp}.{_media_sig(ctx, asset.id, exp)}"
    return {"base": f"/v1/media/{asset.id}/{token}/", "expires_at": exp}


async def read_signed_media(
    ctx: Ctx, asset_id: uuid.UUID, token: str, path: str
) -> tuple[bytes, str]:
    exp_s, _, sig = token.partition(".")
    if not exp_s.isdigit() or int(exp_s) < datetime.now(UTC).timestamp():
        raise ProblemError(404, "not-found", "Not found")
    if not hmac.compare_digest(sig, _media_sig(ctx, asset_id, int(exp_s))):
        raise ProblemError(404, "not-found", "Not found")
    async with system_access(ctx.db, reason="signed media"):
        asset = await ctx.db.get(VideoAsset, asset_id)
        if asset is None:
            raise ProblemError(404, "not-found", "Not found")
        await set_tenant(ctx.db, asset.organization_id)

    def signed(other: VideoAsset) -> str:
        # each part has its own token; same expiry as the playlist's
        return f"{other.id}/{exp_s}.{_media_sig(ctx, other.id, int(exp_s))}/"

    return await read_media_object(ctx, asset, path, signed)

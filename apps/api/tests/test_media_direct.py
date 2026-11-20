"""HLS segments straight from storage (ADR 002 point 7): presigned URLs in the playlists."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import boto3
from botocore.config import Config as BotoConfig

from handball_api.core.config import Settings
from handball_api.core.presign import GetSigner, window_start
from handball_api.core.storage import MemoryStorage, S3Storage, presign_window
from handball_api.models import VideoAsset
from handball_api.services.context import Ctx
from handball_api.services.video_media import (
    SEGMENT_CACHE,
    direct_playlist,
    media_prefix,
    playlist_segments,
    read_media_object,
)

VARIANT = (
    "#EXTM3U\n#EXT-X-VERSION:7\n#EXT-X-TARGETDURATION:4\n"
    '#EXT-X-MAP:URI="init.mp4"\n'
    "#EXTINF:4.000000,\nseg_00000.m4s\n#EXTINF:4.000000,\nseg_00001.m4s\n#EXT-X-ENDLIST\n"
)
MASTER = "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\n720p/index.m3u8\n"


def _settings(**kw: Any) -> Settings:
    return Settings(env="test", log_json=False, **kw)


def _ctx(settings: Settings, storage: Any) -> Ctx:
    none = cast(Any, None)
    return Ctx(db=none, settings=settings, email=none, storage=storage)


def _asset() -> VideoAsset:
    return VideoAsset(id=uuid.uuid4(), organization_id=uuid.uuid4(), match_id=uuid.uuid4())


def test_signer_matches_boto() -> None:
    now = datetime(2026, 11, 20, 7, 0, tzinfo=UTC)
    endpoint = "https://acc.eu.r2.cloudflarestorage.com"
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name="auto",
        aws_access_key_id="AK",
        aws_secret_access_key="SK/with+chars",
        config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    key = "o/m/v/hls/720p/seg_00001.m4s"
    with patch("botocore.auth.get_current_datetime", return_value=now.replace(tzinfo=None)):
        expected = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": "videos", "Key": key, "ResponseCacheControl": SEGMENT_CACHE},
            ExpiresIn=3600,
        )
    ours = GetSigner(endpoint, "auto", "AK", "SK/with+chars", now, 3600).url(
        "videos", key, {"response-cache-control": SEGMENT_CACHE}
    )

    def parts(u: str) -> tuple[str, dict[str, list[str]]]:
        s = urlsplit(u)
        return f"{s.scheme}://{s.netloc}{s.path}", parse_qs(s.query)

    assert parts(ours) == parts(expected)


def test_signer_keeps_a_port_in_the_host() -> None:
    now = datetime(2026, 11, 20, tzinfo=UTC)
    client = boto3.client(
        "s3",
        endpoint_url="http://localhost:8333",
        region_name="eu-central-2",
        aws_access_key_id="a",
        aws_secret_access_key="b",
        config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    with patch("botocore.auth.get_current_datetime", return_value=now.replace(tzinfo=None)):
        expected = client.generate_presigned_url(
            "get_object", Params={"Bucket": "videos", "Key": "a/b.m4s"}, ExpiresIn=600
        )
    ours = GetSigner("http://localhost:8333", "eu-central-2", "a", "b", now, 600).url(
        "videos", "a/b.m4s"
    )
    assert parse_qs(urlsplit(ours).query) == parse_qs(urlsplit(expected).query)


def test_window_and_expiry() -> None:
    assert presign_window(4 * 3600) == 1800
    assert presign_window(24 * 3600) == 3600
    assert presign_window(600) == 60
    now = datetime(2026, 11, 20, 7, 41, 13, tzinfo=UTC)
    assert window_start(now, 1800) == datetime(2026, 11, 20, 7, 30, tzinfo=UTC)


def test_s3_presigned_segments_are_stable_and_long_enough() -> None:
    settings = _settings(
        s3_endpoint_url="http://storage-internal:8333",
        s3_public_endpoint_url="https://acc.eu.r2.cloudflarestorage.com",
        s3_region="auto",
    )
    storage = S3Storage(settings)
    ttl = 4 * 3600
    first = storage.presign_gets("videos", ["k/a.m4s", "k/b.m4s"], ttl, SEGMENT_CACHE)
    again = storage.presign_gets("videos", ["k/a.m4s"], ttl, SEGMENT_CACHE)
    assert first[0] == again[0]  # same window: same URL, the browser cache hits
    u = urlsplit(first[1])
    assert u.netloc == "acc.eu.r2.cloudflarestorage.com"  # the endpoint the browser reaches
    assert u.path == "/videos/k/b.m4s"
    q = parse_qs(u.query)
    signed_at = datetime.strptime(q["X-Amz-Date"][0], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    until = signed_at + timedelta(seconds=int(q["X-Amz-Expires"][0]))
    assert until >= datetime.now(UTC) + timedelta(seconds=ttl - 5)
    assert q["response-cache-control"] == [SEGMENT_CACHE]


def test_segments_of_a_playlist() -> None:
    assert playlist_segments(VARIANT) == ["init.mp4", "seg_00000.m4s", "seg_00001.m4s"]
    assert playlist_segments(MASTER) == []  # variant playlists stay with the API
    already = "#EXTM3U\nhttps://x/videos/a.m4s\n/abs/b.m4s\n"
    assert playlist_segments(already) == []


def test_direct_playlist_signs_only_the_parts_own_media() -> None:
    storage = MemoryStorage()
    c = _ctx(_settings(media_direct=True), storage)
    a = _asset()
    text = direct_playlist(c, a, "hls/720p/index.m3u8", VARIANT.encode()).decode()
    lines = text.splitlines()
    pre = f"https://storage.test/videos/{media_prefix(a)}hls/720p/"
    assert f'#EXT-X-MAP:URI="{pre}init.mp4?' in text
    assert [x.split("?")[0] for x in lines if x.startswith("https://")] == [
        f"{pre}seg_00000.m4s",
        f"{pre}seg_00001.m4s",
    ]
    assert lines.count("#EXTINF:4.000000,") == 2 and lines[-1] == "#EXT-X-ENDLIST"
    # never the original or the analysis proxy, never out of the video's folder
    sneaky = "#EXTM3U\n#EXTINF:4,\n../../proxy.mp4\n#EXTINF:4,\n../../original.mp4\n"
    sneaky += "#EXTINF:4,\n../../../other/hls/720p/seg.m4s\n"
    assert direct_playlist(c, a, "hls/720p/index.m3u8", sneaky.encode()).decode() == sneaky


async def test_read_media_object_direct_and_fallback() -> None:
    storage = MemoryStorage()
    a = _asset()
    await storage.put("videos", media_prefix(a) + "hls/master.m3u8", MASTER.encode(), "x")
    await storage.put("videos", media_prefix(a) + "hls/stream.m3u8", VARIANT.encode(), "x")
    off = _ctx(_settings(), storage)
    on = _ctx(_settings(media_direct=True), storage)
    # off (dev, tests): the playlist as stored, segments through the API
    assert (await read_media_object(off, a, "hls/stream.m3u8"))[0] == VARIANT.encode()
    data, ctype = await read_media_object(on, a, "hls/stream.m3u8")
    assert ctype == "application/vnd.apple.mpegurl"
    assert b"https://storage.test/videos/" in data and b"\nseg_00000.m4s" not in data
    # the master only lists variant playlists: unchanged
    assert (await read_media_object(on, a, "hls/master.m3u8"))[0] == MASTER.encode()
    # a segment asked through the API still answers (old players, offline packs)
    await storage.put("videos", media_prefix(a) + "hls/seg_00000.m4s", b"seg", "x")
    assert (await read_media_object(on, a, "hls/seg_00000.m4s"))[0] == b"seg"

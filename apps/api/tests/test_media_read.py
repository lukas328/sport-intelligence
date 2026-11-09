"""Reading player media from storage: only a missing object is a 404 (no database)."""

from __future__ import annotations

import uuid
from typing import Any, cast

import pytest
from botocore.stub import Stubber

from handball_api.core.config import Settings
from handball_api.core.errors import ProblemError
from handball_api.core.storage import MemoryStorage, ObjectNotFoundError, S3Storage
from handball_api.models import VideoAsset
from handball_api.services import presentations
from handball_api.services.context import Ctx
from handball_api.services.videos import media_prefix, read_media_object


class BrokenStorage(MemoryStorage):
    async def get(self, bucket: str, key: str) -> tuple[bytes, str]:
        raise RuntimeError("storage unavailable")


class Db:
    def __init__(self, asset: VideoAsset) -> None:
        self.asset = asset

    async def get(self, model: Any, key: Any) -> VideoAsset:
        return self.asset


def asset() -> VideoAsset:
    return VideoAsset(id=uuid.uuid4(), organization_id=uuid.uuid4(), match_id=uuid.uuid4())


def ctx(settings: Settings, storage: MemoryStorage, db: Any = None) -> Ctx:
    none = cast(Any, None)
    return Ctx(db=db, settings=settings, email=none, storage=storage)


async def test_read_media_object(settings: Settings) -> None:
    video = asset()
    storage = MemoryStorage()
    bucket = settings.s3_bucket_videos
    await storage.put(bucket, media_prefix(video) + "hls/master.m3u8", b"#EXTM3U", "x")
    await storage.put(bucket, media_prefix(video) + "proxy.mp4", b"proxy", "video/mp4")
    c = ctx(settings, storage)
    assert await read_media_object(c, video, "hls/master.m3u8") == (
        b"#EXTM3U",
        "application/vnd.apple.mpegurl",
    )
    for path in ("hls/missing.m3u8", "proxy.mp4", "original.mov", "../x.jpg", "a.exe"):
        with pytest.raises(ProblemError) as err:
            await read_media_object(c, video, path)
        assert err.value.status == 404, path


async def test_storage_errors_are_not_hidden_as_404(settings: Settings) -> None:
    video = asset()
    with pytest.raises(RuntimeError, match="storage unavailable"):
        await read_media_object(ctx(settings, BrokenStorage()), video, "hls/master.m3u8")
    # presentation stills: missing thumbnails mean no still, a broken storage is an error
    assert await presentations.still(ctx(settings, MemoryStorage(), Db(video)), video.id, 0) is None
    with pytest.raises(RuntimeError):
        await presentations.still(ctx(settings, BrokenStorage(), Db(video)), video.id, 0)


async def test_s3_get_maps_only_missing_keys(settings: Settings) -> None:
    storage = S3Storage(settings)
    with Stubber(storage._client) as stub:
        stub.add_client_error("get_object", service_error_code="NoSuchKey", http_status_code=404)
        stub.add_client_error("get_object", service_error_code="AccessDenied", http_status_code=403)
        with pytest.raises(ObjectNotFoundError):
            await storage.get("videos", "a/missing.jpg")
        with pytest.raises(Exception) as err:
            await storage.get("videos", "a/denied.jpg")
        assert not isinstance(err.value, ObjectNotFoundError)
        assert "AccessDenied" in str(err.value)

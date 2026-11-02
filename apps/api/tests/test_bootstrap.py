from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError

from handball_api.bootstrap import ensure_buckets
from handball_api.core.config import Settings


class FakeS3:
    def __init__(self, existing: set[str]) -> None:
        self.buckets = set(existing)

    def head_bucket(self, *, Bucket: str) -> None:  # noqa: N803
        if Bucket not in self.buckets:
            raise ClientError({"Error": {"Code": "404"}}, "HeadBucket")

    def create_bucket(self, *, Bucket: str) -> dict[str, Any]:  # noqa: N803
        self.buckets.add(Bucket)
        return {}


def test_ensure_buckets_is_idempotent() -> None:
    s3 = FakeS3({"videos"})
    settings = Settings(env="test")
    assert ensure_buckets(settings, s3) == ["artifacts"]
    assert ensure_buckets(settings, s3) == []
    assert s3.buckets == {"videos", "artifacts"}

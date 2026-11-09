from __future__ import annotations

from typing import Any

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from handball_api import bootstrap
from handball_api.bootstrap import BootstrapError, cors_rule, ensure_buckets
from handball_api.core.config import Settings


def _err(code: str, op: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "x"}}, op)


class FakeS3:
    """Records writes; `deny` lists operations the key may not call (object-scoped token)."""

    def __init__(
        self,
        existing: set[str],
        *,
        deny: set[str] | None = None,
        cors: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        self.buckets = set(existing)
        self.deny = deny or set()
        self.cors_rules = dict(cors or {})
        self.writes: list[str] = []

    def _check(self, op: str) -> None:
        if op in self.deny:
            raise _err("AccessDenied", op)

    def head_bucket(self, *, Bucket: str) -> None:  # noqa: N803
        self._check("HeadBucket")
        if Bucket not in self.buckets:
            raise _err("404", "HeadBucket")

    def create_bucket(self, *, Bucket: str) -> dict[str, Any]:  # noqa: N803
        self._check("CreateBucket")
        self.writes.append(f"create:{Bucket}")
        self.buckets.add(Bucket)
        return {}

    def get_bucket_cors(self, *, Bucket: str) -> dict[str, Any]:  # noqa: N803
        self._check("GetBucketCors")
        if Bucket not in self.cors_rules:
            raise _err("NoSuchCORSConfiguration", "GetBucketCors")
        return {"CORSRules": self.cors_rules[Bucket]}

    def put_bucket_cors(self, *, Bucket: str, CORSConfiguration: Any) -> None:  # noqa: N803
        self._check("PutBucketCors")
        self.writes.append(f"cors:{Bucket}")
        self.cors_rules[Bucket] = CORSConfiguration["CORSRules"]


SETTINGS = Settings(env="test")


def test_ensure_buckets_is_idempotent() -> None:
    s3 = FakeS3({"videos"})
    first = ensure_buckets(SETTINGS, s3)
    assert first.created == ["artifacts"] and first.cors_updated and not first.manual_steps
    second = ensure_buckets(SETTINGS, s3)
    assert second.created == [] and not second.cors_updated and not second.manual_steps
    assert s3.buckets == {"videos", "artifacts"}
    assert s3.writes == ["create:artifacts", "cors:videos"]  # nothing written the second time
    assert s3.cors_rules["videos"][0]["ExposeHeaders"] == ["ETag"]


def test_object_scoped_key_with_ready_buckets_writes_nothing() -> None:
    rule = {**cors_rule(SETTINGS), "AllowedMethods": ["get", "PUT", "HEAD", "POST"]}
    s3 = FakeS3(
        {"videos", "artifacts"},
        deny={"CreateBucket", "PutBucketCors"},
        cors={"videos": [rule]},
    )
    result = ensure_buckets(SETTINGS, s3)
    assert result.created == [] and not result.manual_steps and s3.writes == []


def test_denied_cors_is_a_manual_step_not_a_failure() -> None:
    s3 = FakeS3({"videos", "artifacts"}, deny={"CreateBucket", "PutBucketCors", "GetBucketCors"})
    result = ensure_buckets(SETTINGS, s3)
    assert not result.cors_updated
    assert len(result.manual_steps) == 1
    assert "set this rule by hand" in result.manual_steps[0]
    assert "ETag" in result.manual_steps[0]


def test_outdated_cors_is_replaced() -> None:
    old = {**cors_rule(SETTINGS), "AllowedOrigins": ["https://old.example"]}
    s3 = FakeS3({"videos", "artifacts"}, cors={"videos": [old]})
    assert ensure_buckets(SETTINGS, s3).cors_updated
    assert s3.cors_rules["videos"] == [cors_rule(SETTINGS)]


def test_unverifiable_bucket_is_a_manual_step() -> None:
    s3 = FakeS3(set(), deny={"HeadBucket", "CreateBucket", "PutBucketCors", "GetBucketCors"})
    result = ensure_buckets(SETTINGS, s3)
    assert result.created == []
    assert sum("make sure it exists" in s for s in result.manual_steps) == 2


def test_missing_bucket_that_cannot_be_created_fails() -> None:
    s3 = FakeS3({"videos"}, deny={"CreateBucket"})
    with pytest.raises(BootstrapError, match=r"'artifacts' does not exist.*create it by hand"):
        ensure_buckets(SETTINGS, s3)


def test_other_storage_errors_still_fail() -> None:
    class Broken(FakeS3):
        def head_bucket(self, *, Bucket: str) -> None:  # noqa: N803
            raise _err("InvalidAccessKeyId", "HeadBucket")

    with pytest.raises(BootstrapError, match="InvalidAccessKeyId"):
        ensure_buckets(SETTINGS, Broken(set()))

    class BadCors(FakeS3):
        def put_bucket_cors(self, *, Bucket: str, CORSConfiguration: Any) -> None:  # noqa: N803
            raise _err("MalformedXML", "PutBucketCors")

    with pytest.raises(BootstrapError, match="MalformedXML"):
        ensure_buckets(SETTINGS, BadCors({"videos", "artifacts"}))


def test_main_exit_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap, "get_settings", lambda: SETTINGS)
    monkeypatch.setattr(
        bootstrap,
        "s3_client",
        lambda _s: FakeS3({"videos", "artifacts"}, deny={"PutBucketCors", "GetBucketCors"}),
    )
    assert bootstrap.main() == 0  # manual step only: the migration job must still succeed

    monkeypatch.setattr(bootstrap, "s3_client", lambda _s: FakeS3(set(), deny={"CreateBucket"}))
    assert bootstrap.main() == 1

    class Unreachable(FakeS3):
        def head_bucket(self, *, Bucket: str) -> None:  # noqa: N803
            raise EndpointConnectionError(endpoint_url="https://storage.invalid")

    monkeypatch.setattr(bootstrap, "s3_client", lambda _s: Unreachable(set()))
    assert bootstrap.main() == 1

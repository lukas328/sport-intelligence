"""Idempotent environment bootstrap run after migrations: creates the object storage buckets.

Production keys are often scoped to objects (R2 "Object Read & Write", S3 policies without
`s3:CreateBucket`/`s3:PutBucketCORS`). The bootstrap therefore looks first and only writes what is
missing. When the key may not write it, the step is logged as a manual task for the operator and
the job still succeeds; a bucket that is missing and cannot be created stays a hard error.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any, Protocol

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from handball_api.core.config import Settings, get_settings
from handball_api.core.logging import configure_logging, get_logger

log = get_logger("bootstrap")

DENIED = {"AccessDenied", "403", "Forbidden", "AllAccessDisabled", "Unauthorized"}
MISSING_BUCKET = {"404", "NoSuchBucket", "NotFound"}
NO_CORS = {"NoSuchCORSConfiguration", "NoSuchCors", "404"}


class BucketClient(Protocol):
    def head_bucket(self, *, Bucket: str) -> Any: ...  # noqa: N803 (boto3 signature)

    def create_bucket(self, *, Bucket: str) -> Any: ...  # noqa: N803

    def get_bucket_cors(self, *, Bucket: str) -> Any: ...  # noqa: N803

    def put_bucket_cors(self, *, Bucket: str, CORSConfiguration: Any) -> Any: ...  # noqa: N803


class BootstrapError(RuntimeError):
    """A problem the operator must fix before the environment works (exit code 1)."""


@dataclass
class BootstrapResult:
    created: list[str] = field(default_factory=list)
    cors_updated: bool = False
    manual_steps: list[str] = field(default_factory=list)


def s3_client(settings: Settings) -> BucketClient:
    client: BucketClient = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
    )
    return client


def _code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))


def cors_rule(settings: Settings) -> dict[str, Any]:
    # Browsers upload parts directly to storage (presigned URLs) and need the ETag header.
    return {
        "AllowedOrigins": [settings.web_base_url, *settings.cors_origins],
        "AllowedMethods": ["PUT", "GET", "HEAD"],
        "AllowedHeaders": ["*"],
        "ExposeHeaders": ["ETag"],
        "MaxAgeSeconds": 3600,
    }


def _covers(existing: dict[str, Any], wanted: dict[str, Any]) -> bool:
    def upper(key: str, rule: dict[str, Any]) -> set[str]:
        return {str(v).upper() for v in rule.get(key, [])}

    return (
        {str(o) for o in wanted["AllowedOrigins"]}
        <= {str(o) for o in existing.get("AllowedOrigins", [])}
        and upper("AllowedMethods", wanted) <= upper("AllowedMethods", existing)
        and "*" in {str(h) for h in existing.get("AllowedHeaders", [])}
        and upper("ExposeHeaders", wanted) <= upper("ExposeHeaders", existing)
    )


def _ensure_bucket(s3: BucketClient, bucket: str, result: BootstrapResult) -> None:
    try:
        s3.head_bucket(Bucket=bucket)
        return
    except ClientError as exc:
        code = _code(exc)
        if code in DENIED:
            # The key may not inspect the bucket (object-scoped token); uploads will tell.
            log.warning("bucket_unverifiable", bucket=bucket, code=code)
            result.manual_steps.append(
                f"Could not check bucket '{bucket}' with this key: make sure it exists."
            )
            return
        if code not in MISSING_BUCKET:
            raise BootstrapError(f"Checking bucket '{bucket}' failed ({code}).") from exc
    try:
        s3.create_bucket(Bucket=bucket)
    except ClientError as exc:
        code = _code(exc)
        if code == "BucketAlreadyOwnedByYou":
            return
        if code in DENIED:
            raise BootstrapError(
                f"Bucket '{bucket}' does not exist and this key may not create it ({code}): "
                "create it by hand in the storage console, then rerun the job."
            ) from exc
        raise BootstrapError(f"Creating bucket '{bucket}' failed ({code}).") from exc
    result.created.append(bucket)


def _ensure_cors(
    s3: BucketClient, bucket: str, rule: dict[str, Any], result: BootstrapResult
) -> None:
    try:
        current = s3.get_bucket_cors(Bucket=bucket).get("CORSRules", [])
        if any(_covers(r, rule) for r in current):
            return
    except ClientError as exc:
        code = _code(exc)
        if code not in NO_CORS and code not in DENIED:
            raise BootstrapError(f"Reading the CORS rules of '{bucket}' failed ({code}).") from exc
    try:
        s3.put_bucket_cors(Bucket=bucket, CORSConfiguration={"CORSRules": [rule]})
    except ClientError as exc:
        code = _code(exc)
        if code not in DENIED:
            raise BootstrapError(f"Setting the CORS rules of '{bucket}' failed ({code}).") from exc
        log.warning("bucket_cors_manual", bucket=bucket, code=code, wanted=rule)
        result.manual_steps.append(
            f"This key may not set CORS on '{bucket}' ({code}): set this rule by hand in the "
            f"storage console, otherwise browser uploads fail: {json.dumps(rule)}"
        )
        return
    result.cors_updated = True


def ensure_buckets(settings: Settings, client: BucketClient | None = None) -> BootstrapResult:
    s3 = client or s3_client(settings)
    result = BootstrapResult()
    for bucket in (settings.s3_bucket_videos, settings.s3_bucket_artifacts):
        _ensure_bucket(s3, bucket, result)
    _ensure_cors(s3, settings.s3_bucket_videos, cors_rule(settings), result)
    return result


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    try:
        result = ensure_buckets(settings)
    except BootstrapError as exc:
        log.error("bootstrap_failed", reason=str(exc))
        return 1
    except BotoCoreError as exc:  # wrong endpoint, DNS, TLS, missing credentials
        log.error("bootstrap_failed", reason=f"Object storage not reachable: {exc}")
        return 1
    for step in result.manual_steps:
        log.warning("bootstrap_manual_step", action=step)
    log.info(
        "buckets_ready",
        created=result.created,
        cors_updated=result.cors_updated,
        manual_steps=len(result.manual_steps),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

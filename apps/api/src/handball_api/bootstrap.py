"""Idempotent environment bootstrap run after migrations: creates the object storage buckets."""

from __future__ import annotations

from typing import Any, Protocol

import boto3
from botocore.exceptions import ClientError

from handball_api.core.config import Settings, get_settings
from handball_api.core.logging import configure_logging, get_logger


class BucketClient(Protocol):
    def head_bucket(self, *, Bucket: str) -> Any: ...  # noqa: N803 (boto3 signature)

    def create_bucket(self, *, Bucket: str) -> Any: ...  # noqa: N803

    def put_bucket_cors(self, *, Bucket: str, CORSConfiguration: Any) -> Any: ...  # noqa: N803


def s3_client(settings: Settings) -> BucketClient:
    client: BucketClient = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
    )
    return client


def ensure_buckets(settings: Settings, client: BucketClient | None = None) -> list[str]:
    s3 = client or s3_client(settings)
    created: list[str] = []
    for bucket in (settings.s3_bucket_videos, settings.s3_bucket_artifacts):
        try:
            s3.head_bucket(Bucket=bucket)
        except ClientError:
            s3.create_bucket(Bucket=bucket)
            created.append(bucket)
    # Browsers upload parts directly to storage (presigned URLs) and need the ETag header.
    s3.put_bucket_cors(
        Bucket=settings.s3_bucket_videos,
        CORSConfiguration={
            "CORSRules": [
                {
                    "AllowedOrigins": [settings.web_base_url, *settings.cors_origins],
                    "AllowedMethods": ["PUT", "GET", "HEAD"],
                    "AllowedHeaders": ["*"],
                    "ExposeHeaders": ["ETag"],
                    "MaxAgeSeconds": 3600,
                }
            ]
        },
    )
    return created


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    created = ensure_buckets(settings)
    get_logger("bootstrap").info("buckets_ready", created=created)


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path
from typing import Any

import boto3
from boto3.s3.transfer import TransferConfig

TRANSFER = TransferConfig(
    multipart_threshold=64 * 1024**2, multipart_chunksize=64 * 1024**2, max_concurrency=4
)
CONTENT_TYPES = {
    ".m3u8": "application/vnd.apple.mpegurl",
    ".m4s": "video/iso.segment",
    ".mp4": "video/mp4",
    ".jpg": "image/jpeg",
    ".vtt": "text/vtt",
    ".json": "application/json",
    ".parquet": "application/vnd.apache.parquet",
    ".bin": "application/octet-stream",
}


def s3_client(endpoint: str | None, region: str, access_key: str, secret_key: str) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


def upload_dir(s3: Any, bucket: str, local: Path, prefix: str) -> list[str]:
    keys = []
    for path in sorted(p for p in local.rglob("*") if p.is_file()):
        key = prefix + path.relative_to(local).as_posix()
        s3.upload_file(
            str(path),
            bucket,
            key,
            Config=TRANSFER,
            ExtraArgs={"ContentType": CONTENT_TYPES.get(path.suffix, "application/octet-stream")},
        )
        keys.append(key)
    return keys

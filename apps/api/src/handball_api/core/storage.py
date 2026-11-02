"""Object storage port (S3-compatible adapter + in-memory adapter for tests)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Protocol

import boto3
from botocore.exceptions import ClientError

from handball_api.core.config import Settings


class ObjectNotFoundError(Exception):
    pass


class ObjectStorage(Protocol):
    async def put(self, bucket: str, key: str, data: bytes, content_type: str) -> None: ...

    async def get(self, bucket: str, key: str) -> tuple[bytes, str]: ...

    async def delete(self, bucket: str, key: str) -> None: ...


@dataclass
class MemoryStorage:
    objects: dict[tuple[str, str], tuple[bytes, str]] = field(default_factory=dict)

    async def put(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        self.objects[(bucket, key)] = (data, content_type)

    async def get(self, bucket: str, key: str) -> tuple[bytes, str]:
        try:
            return self.objects[(bucket, key)]
        except KeyError as exc:
            raise ObjectNotFoundError(key) from exc

    async def delete(self, bucket: str, key: str) -> None:
        self.objects.pop((bucket, key), None)


class S3Storage:
    def __init__(self, settings: Settings) -> None:
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
        )

    async def put(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object, Bucket=bucket, Key=key, Body=data, ContentType=content_type
        )

    async def get(self, bucket: str, key: str) -> tuple[bytes, str]:
        def _get() -> tuple[bytes, str]:
            try:
                obj = self._client.get_object(Bucket=bucket, Key=key)
            except ClientError as exc:
                raise ObjectNotFoundError(key) from exc
            return obj["Body"].read(), obj.get("ContentType", "application/octet-stream")

        return await asyncio.to_thread(_get)

    async def delete(self, bucket: str, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=bucket, Key=key)

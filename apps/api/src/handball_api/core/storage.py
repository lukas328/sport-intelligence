"""Object storage port (S3-compatible adapter + in-memory adapter for tests).

Large uploads go directly from the browser to storage with presigned multipart part URLs;
the API only orchestrates (BRIEF 6.2). Listing uploaded parts makes uploads resumable.
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from handball_api.core.config import Settings


class ObjectNotFoundError(Exception):
    pass


def _is_not_found(exc: ClientError) -> bool:
    code = str(exc.response.get("Error", {}).get("Code", ""))
    return code in ("NoSuchKey", "NotFound", "404")


@dataclass(frozen=True, slots=True)
class UploadedPart:
    number: int
    etag: str
    size: int


class ObjectStorage(Protocol):
    async def put(self, bucket: str, key: str, data: bytes, content_type: str) -> None: ...

    async def get(self, bucket: str, key: str) -> tuple[bytes, str]: ...

    async def delete(self, bucket: str, key: str) -> None: ...

    async def delete_prefix(self, bucket: str, prefix: str) -> int: ...

    async def create_multipart(self, bucket: str, key: str, content_type: str) -> str: ...

    async def presign_part(self, bucket: str, key: str, upload_id: str, number: int) -> str: ...

    async def list_parts(self, bucket: str, key: str, upload_id: str) -> list[UploadedPart]: ...

    async def complete_multipart(
        self, bucket: str, key: str, upload_id: str, parts: list[tuple[int, str]]
    ) -> None: ...

    async def abort_multipart(self, bucket: str, key: str, upload_id: str) -> None: ...

    async def size(self, bucket: str, key: str) -> int: ...


@dataclass
class MemoryStorage:
    objects: dict[tuple[str, str], tuple[bytes, str]] = field(default_factory=dict)
    uploads: dict[str, dict[int, bytes]] = field(default_factory=dict)

    async def put(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        self.objects[(bucket, key)] = (data, content_type)

    async def get(self, bucket: str, key: str) -> tuple[bytes, str]:
        try:
            return self.objects[(bucket, key)]
        except KeyError as exc:
            raise ObjectNotFoundError(key) from exc

    async def delete(self, bucket: str, key: str) -> None:
        self.objects.pop((bucket, key), None)

    async def delete_prefix(self, bucket: str, prefix: str) -> int:
        keys = [k for k in self.objects if k[0] == bucket and k[1].startswith(prefix)]
        for k in keys:
            del self.objects[k]
        return len(keys)

    async def create_multipart(self, bucket: str, key: str, content_type: str) -> str:
        upload_id = uuid.uuid4().hex
        self.uploads[upload_id] = {}
        return upload_id

    async def presign_part(self, bucket: str, key: str, upload_id: str, number: int) -> str:
        return f"memory://{bucket}/{key}?uploadId={upload_id}&partNumber={number}"

    def upload_part(self, upload_id: str, number: int, data: bytes) -> str:
        """Test helper: what the browser does with the presigned URL."""
        self.uploads[upload_id][number] = data
        return hashlib.md5(data, usedforsecurity=False).hexdigest()

    async def list_parts(self, bucket: str, key: str, upload_id: str) -> list[UploadedPart]:
        if upload_id not in self.uploads:
            raise ObjectNotFoundError(upload_id)
        return [
            UploadedPart(n, hashlib.md5(d, usedforsecurity=False).hexdigest(), len(d))
            for n, d in sorted(self.uploads[upload_id].items())
        ]

    async def complete_multipart(
        self, bucket: str, key: str, upload_id: str, parts: list[tuple[int, str]]
    ) -> None:
        stored = self.uploads.pop(upload_id)
        data = b""
        for number, etag in sorted(parts):
            chunk = stored.get(number)
            if chunk is None or hashlib.md5(chunk, usedforsecurity=False).hexdigest() != etag:
                raise ValueError(f"part {number} missing or etag mismatch")
            data += chunk
        self.objects[(bucket, key)] = (data, "application/octet-stream")

    async def abort_multipart(self, bucket: str, key: str, upload_id: str) -> None:
        self.uploads.pop(upload_id, None)

    async def size(self, bucket: str, key: str) -> int:
        return len((await self.get(bucket, key))[0])


class S3Storage:
    def __init__(self, settings: Settings) -> None:
        def client(endpoint: str | None) -> Any:
            return boto3.client(
                "s3",
                endpoint_url=endpoint,
                region_name=settings.s3_region,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
                config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
            )

        self._client = client(settings.s3_endpoint_url)
        # Presigned URLs must carry the host the browser reaches (signature covers the host).
        self._public = client(settings.s3_public_endpoint_url or settings.s3_endpoint_url)
        self._ttl = settings.presign_ttl_s

    async def put(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object, Bucket=bucket, Key=key, Body=data, ContentType=content_type
        )

    async def get(self, bucket: str, key: str) -> tuple[bytes, str]:
        def _get() -> tuple[bytes, str]:
            try:
                obj = self._client.get_object(Bucket=bucket, Key=key)
            except ClientError as exc:
                if _is_not_found(exc):
                    raise ObjectNotFoundError(key) from exc
                raise  # access denied, outage: not a missing object
            return obj["Body"].read(), obj.get("ContentType", "application/octet-stream")

        return await asyncio.to_thread(_get)

    async def delete(self, bucket: str, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=bucket, Key=key)

    async def delete_prefix(self, bucket: str, prefix: str) -> int:
        def _run() -> int:
            count = 0
            paginator = self._client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                keys = [{"Key": o["Key"]} for o in page.get("Contents", [])]
                if keys:
                    self._client.delete_objects(Bucket=bucket, Delete={"Objects": keys})
                    count += len(keys)
            return count

        return await asyncio.to_thread(_run)

    async def create_multipart(self, bucket: str, key: str, content_type: str) -> str:
        r = await asyncio.to_thread(
            self._client.create_multipart_upload, Bucket=bucket, Key=key, ContentType=content_type
        )
        return str(r["UploadId"])

    async def presign_part(self, bucket: str, key: str, upload_id: str, number: int) -> str:
        url: str = await asyncio.to_thread(
            self._public.generate_presigned_url,
            "upload_part",
            Params={"Bucket": bucket, "Key": key, "UploadId": upload_id, "PartNumber": number},
            ExpiresIn=self._ttl,
        )
        return url

    async def list_parts(self, bucket: str, key: str, upload_id: str) -> list[UploadedPart]:
        def _run() -> list[UploadedPart]:
            parts: list[UploadedPart] = []
            marker = 0
            while True:
                try:
                    r = self._client.list_parts(
                        Bucket=bucket, Key=key, UploadId=upload_id, PartNumberMarker=marker
                    )
                except ClientError as exc:
                    raise ObjectNotFoundError(upload_id) from exc
                parts += [
                    UploadedPart(p["PartNumber"], p["ETag"].strip('"'), p["Size"])
                    for p in r.get("Parts", [])
                ]
                if not r.get("IsTruncated"):
                    return parts
                marker = r["NextPartNumberMarker"]

        return await asyncio.to_thread(_run)

    async def complete_multipart(
        self, bucket: str, key: str, upload_id: str, parts: list[tuple[int, str]]
    ) -> None:
        await asyncio.to_thread(
            self._client.complete_multipart_upload,
            Bucket=bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={"Parts": [{"PartNumber": n, "ETag": e} for n, e in sorted(parts)]},
        )

    async def abort_multipart(self, bucket: str, key: str, upload_id: str) -> None:
        await asyncio.to_thread(
            self._client.abort_multipart_upload, Bucket=bucket, Key=key, UploadId=upload_id
        )

    async def size(self, bucket: str, key: str) -> int:
        def _run() -> int:
            try:
                return int(self._client.head_object(Bucket=bucket, Key=key)["ContentLength"])
            except ClientError as exc:
                raise ObjectNotFoundError(key) from exc

        return await asyncio.to_thread(_run)

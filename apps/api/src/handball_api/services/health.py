"""Readiness checks for the backing services (Postgres, Redis, object storage)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

import boto3
from botocore.config import Config as BotoConfig
from redis.asyncio import Redis
from sqlalchemy import text

from handball_api.core.config import Settings
from handball_api.core.db import get_engine

Status = Literal["ok", "error"]
Check = Callable[[], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    status: Status
    latency_ms: float
    error: str | None = None


async def _run(name: str, check: Check, timeout_s: float) -> CheckResult:
    start = time.perf_counter()
    try:
        await asyncio.wait_for(check(), timeout=timeout_s)
    except Exception as exc:
        return CheckResult(
            name, "error", (time.perf_counter() - start) * 1000, f"{type(exc).__name__}"
        )
    return CheckResult(name, "ok", (time.perf_counter() - start) * 1000)


async def run_checks(checks: dict[str, Check], timeout_s: float) -> list[CheckResult]:
    return list(await asyncio.gather(*(_run(n, c, timeout_s) for n, c in checks.items())))


def default_checks(settings: Settings) -> dict[str, Check]:
    async def database() -> None:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))

    async def redis() -> None:
        client = Redis.from_url(settings.redis_url)
        try:
            await client.ping()
        finally:
            await client.aclose()

    async def storage() -> None:
        def head() -> None:
            s3 = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                region_name=settings.s3_region,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
                config=BotoConfig(connect_timeout=1, read_timeout=1, retries={"max_attempts": 1}),
            )
            s3.head_bucket(Bucket=settings.s3_bucket_videos)

        await asyncio.to_thread(head)

    return {"database": database, "redis": redis, "storage": storage}

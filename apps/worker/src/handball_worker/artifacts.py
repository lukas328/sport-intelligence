"""The frame of a job that renders one file for the API (presentation export, highlight reel): a
work folder, the source videos downloaded into it, the result uploaded and the outcome reported
back to the API, also when rendering failed (the coach sees the error)."""

from __future__ import annotations

import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import httpx

from handball_worker.config import WorkerSettings

# settings, S3 client, work folder, downloaded sources (id -> local file) -> the rendered file
Build = Callable[[WorkerSettings, Any, Path, dict[str, Path]], Path]


def run_artifact_job(
    payload: dict[str, Any],
    *,
    callback_path: str,
    build: Build,
    log: Any,
    failed_event: str,
    sources: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Renders with `build` and uploads the file to `payload["out_key"]` (artifacts bucket);
    `sources` (id -> key in the videos bucket) are downloaded first. The outcome is posted to
    the API at `callback_path` and returned."""
    settings = WorkerSettings()
    s3 = settings.s3()
    url = f"{settings.api_internal_url.rstrip('/')}{callback_path}"
    headers = {"x-internal-token": settings.internal_token}
    try:
        with tempfile.TemporaryDirectory(
            dir=settings.work_dir if Path(settings.work_dir).exists() else None
        ) as tmp:
            work = Path(tmp)
            local: dict[str, Path] = {}
            for vid, key in (sources or {}).items():
                dst = work / f"src_{vid}.mp4"
                s3.download_file(payload["bucket_videos"], key, str(dst))
                local[vid] = dst
            final = build(settings, s3, work, local)
            s3.upload_file(
                str(final),
                payload["bucket_artifacts"],
                payload["out_key"],
                ExtraArgs={"ContentType": "video/mp4"},
            )
        body: dict[str, Any] = {"status": "ready", "key": payload["out_key"]}
    except Exception as exc:  # reported to the API
        log.warning(failed_event, error=str(exc))
        body = {"status": "failed", "error": str(exc)[:500]}
    httpx.post(url, json=body, headers=headers, timeout=30).raise_for_status()
    return body

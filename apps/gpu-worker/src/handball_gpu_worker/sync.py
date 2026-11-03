"""Camera sync by audio (BRIEF 7.2 stage 0): offset of a goal cam against the main video."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

import structlog

from handball_jobkit import TRANSFER, JobSettings, Reporter, s3_client
from handball_vision.audio import estimate_offset, load_mono

log = structlog.get_logger("gpu.sync")

STAGES = {"download": 0.4, "sync": 0.6}


def run_sync(
    job_id: str,
    bucket: str,
    main_audio_key: str,
    other_audio_key: str,
    settings: JobSettings | None = None,
    reporter: Reporter | None = None,
    **_: Any,
) -> dict[str, Any]:
    settings = settings or JobSettings()
    rep = reporter or Reporter(settings.api_internal_url, settings.internal_token, job_id, STAGES)
    Path(settings.work_dir).mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f"sync-{job_id}-", dir=settings.work_dir))
    try:
        s3 = s3_client(
            settings.s3_endpoint_url,
            settings.s3_region,
            settings.s3_access_key,
            settings.s3_secret_key,
        )
        rep.stage("download")
        main, other = work / "main.wav", work / "other.wav"
        s3.download_file(bucket, main_audio_key, str(main), Config=TRANSFER)
        s3.download_file(bucket, other_audio_key, str(other), Config=TRANSFER)
        rep.stage("sync")
        res = estimate_offset(load_mono(main), load_mono(other))
        payload = {"offset_ms": res.offset_ms, "confidence": res.confidence}
        rep.succeed(payload)
        log.info("sync_done", job_id=job_id, **payload)
        return payload
    except Exception as exc:
        rep.fail(f"{type(exc).__name__}: {exc}")
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)

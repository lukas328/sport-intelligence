"""Pipeline stages 2 to 5 on the analysis proxy (BRIEF 7.2).

Runs on the `gpu` queue (local backend on CPU until a GPU provider is configured). Writes:
- `analysis/tracks.parquet`: all track points (pipeline and detector version in the metadata)
- `analysis/chunk_NNNNN.bin`: 30 s chunks for the browser, packed little-endian float32 rows
  [t_ms, track_id, x, y] (BRIEF 6.4: compact binary instead of JSON)
and reports calibration, per-track summary, timings and cost to the API.
"""

from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
import structlog

from handball_jobkit import TRANSFER, JobSettings, Reporter, s3_client, upload_dir
from handball_vision import __version__ as vision_version
from handball_vision import formation
from handball_vision.calibration import CalibrationError, calibrate_points
from handball_vision.pipeline import AnalysisResult, analyse_video
from handball_vision.teams import hex_to_bgr

log = structlog.get_logger("gpu.analysis")

STAGES = {"download": 0.05, "calibration": 0.1, "tracking": 0.75, "upload": 0.1}
CHUNK_MS = 30_000


def write_chunks(result: AnalysisResult, out: Path) -> int:
    rows = np.array(
        [[round(p.frame * 1000 / result.fps), p.track_id, p.x, p.y] for p in result.points],
        dtype=np.float32,
    ).reshape(-1, 4)
    count = 0
    if len(rows) == 0:
        return 0
    last = int(rows[:, 0].max()) // CHUNK_MS
    for n in range(last + 1):
        sel = rows[(rows[:, 0] >= n * CHUNK_MS) & (rows[:, 0] < (n + 1) * CHUNK_MS)]
        (out / f"chunk_{n:05d}.bin").write_bytes(sel.astype("<f4").tobytes())
        count += 1
    return count


def events_payload(result: AnalysisResult) -> dict[str, Any]:
    """Automatic events and possession phases (addendum 01, A3) for the API."""
    found = result.detect_events()
    return {
        "events": [
            {
                "t_ms": e.t_ms,
                "type": e.type,
                "team": e.team,
                "confidence": e.confidence,
                **e.attributes,
            }
            for e in found.events
        ],
        "possessions": [
            {
                "team": p.team,
                "start_ms": p.start_ms,
                "end_ms": p.end_ms,
                "confidence": p.confidence,
                "outcome": p.outcome,
            }
            for p in found.possessions
        ],
        "sides": [{"from_ms": t, "home_defends": side} for t, side in found.sides],
        "missing": found.missing,
    }


def detect_formations(result: AnalysisResult) -> list[dict[str, Any]]:
    labels = {tid: str(v.get("label")) for tid, v in result.teams.items() if v.get("label")}
    samples = [
        formation.Sample(
            round(p.frame * 1000 / result.fps), p.track_id, labels[p.track_id], p.x, p.y
        )
        for p in result.points
        if p.track_id in labels
    ]
    return [s.to_dict() for s in formation.detect(samples)]


def run_analysis(
    job_id: str,
    organization_id: str,
    match_id: str,
    asset_id: str,
    bucket: str,
    proxy_key: str,
    prefix: str,
    kits: dict[str, str],
    calibration_points: list[dict[str, list[float]]] | None = None,
    settings: JobSettings | None = None,
    reporter: Reporter | None = None,
) -> dict[str, Any]:
    settings = settings or JobSettings()
    rep = reporter or Reporter(settings.api_internal_url, settings.internal_token, job_id, STAGES)
    Path(settings.work_dir).mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f"analysis-{asset_id}-", dir=settings.work_dir))
    started = time.perf_counter()
    try:
        s3 = s3_client(
            settings.s3_endpoint_url,
            settings.s3_region,
            settings.s3_access_key,
            settings.s3_secret_key,
        )
        rep.stage("download")
        video = work / "proxy.mp4"
        s3.download_file(bucket, proxy_key, str(video), Config=TRANSFER)

        rep.stage("calibration")
        calib = None
        if calibration_points:
            import av

            with av.open(str(video)) as c:
                st = c.streams.video[0]
                size = (st.codec_context.width, st.codec_context.height)
            calib = calibrate_points(
                [(p["image"][0], p["image"][1]) for p in calibration_points],
                [(p["court"][0], p["court"][1]) for p in calibration_points],
                size,
            )
        bgr = {k: hex_to_bgr(v) for k, v in kits.items()}
        rep.stage("tracking")
        result = analyse_video(
            video,
            bgr,
            calibration=calib,
            progress=lambda stage, f: rep.fraction(f) if stage == "tracking" else None,
        )

        rep.stage("upload")
        out = work / "analysis"
        out.mkdir()
        result.write_parquet(out / "tracks.parquet")
        chunks = write_chunks(result, out)
        upload_dir(s3, settings.s3_bucket_artifacts, out, prefix + "analysis/")
        elapsed = time.perf_counter() - started
        tracks = result.summary()
        payload: dict[str, Any] = {
            "calibration": result.calibration.to_dict(),
            "tracks": tracks,
            "fps": result.fps,
            "frames": result.frames,
            "chunks": chunks,
            "chunk_ms": CHUNK_MS,
            "detector": result.detector_source,
            "versions": {"vision": vision_version},
            "timings_s": {k: round(v, 2) for k, v in result.timings_s.items()},
            "elapsed_s": round(elapsed, 1),
            "stats": result.extra,
            "formations": detect_formations(result),
            "events": events_payload(result),
        }
        rep.succeed(payload)
        log.info(
            "analysis_done",
            job_id=job_id,
            tracks=len(payload["tracks"]),
            elapsed_s=payload["elapsed_s"],
        )
        return payload
    except CalibrationError as exc:
        rep.fail(f"calibration: {exc}")
        raise
    except Exception as exc:
        rep.fail(f"{type(exc).__name__}: {exc}")
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)

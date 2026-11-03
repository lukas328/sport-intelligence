"""Pipeline stage 0 and 1: ingest and quality check (BRIEF 7.2).

run_ingest: download original, checksum, ffprobe, heuristic quality check, HLS ladder (1080p/720p),
analysis proxy (1280 px, 25 fps), poster and thumbnail sprite, upload outputs.
run_import: fetch a video from a public https link into storage (SSRF-checked on every hop).
"""

from __future__ import annotations

import hashlib
import ipaddress
import shutil
import socket
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import boto3
import httpx
import structlog

from handball_jobkit import TRANSFER, Reporter, upload_dir
from handball_worker.config import WorkerSettings
from handball_worker.media import quality, transcode
from handball_worker.media.probe import ProbeError, probe

log = structlog.get_logger("worker.ingest")

INGEST_STAGES = {
    "download": 0.08,
    "probe": 0.02,
    "quality": 0.05,
    "transcode": 0.55,
    "proxy": 0.2,
    "thumbnails": 0.05,
    "upload": 0.05,
}
IMPORT_STAGES = {"download": 0.9, "upload": 0.1}


def _s3(settings: WorkerSettings) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_ingest(
    job_id: str,
    organization_id: str,
    match_id: str,
    asset_id: str,
    bucket: str,
    key: str,
    prefix: str,
    settings: WorkerSettings | None = None,
    reporter: Reporter | None = None,
) -> dict[str, Any]:
    settings = settings or WorkerSettings()
    rep = reporter or Reporter(
        settings.api_internal_url, settings.internal_token, job_id, INGEST_STAGES
    )
    work = Path(tempfile.mkdtemp(prefix=f"ingest-{asset_id}-", dir=_workdir(settings)))
    log.info("ingest_start", job_id=job_id, asset_id=asset_id)
    try:
        s3 = _s3(settings)
        rep.stage("download")
        src = work / ("original" + Path(key).suffix)
        s3.download_file(bucket, key, str(src), Config=TRANSFER)
        checksum = sha256_file(src)

        rep.stage("probe")
        info = probe(src, settings.ffprobe)

        rep.stage("quality")
        windows = transcode.sample_gray_frames(src, info, settings.ffmpeg)
        q = quality.report(info, quality.analyse_windows(windows))

        rep.stage("transcode")
        out = work / "out"
        hls = out / "hls"
        hls.mkdir(parents=True)
        transcode.run_with_progress(
            transcode.hls_command(
                src, hls, info, settings.ffmpeg, settings.x264_preset, settings.hls_segment_s
            ),
            info.duration_s,
            rep.fraction,
        )

        rep.stage("proxy")
        transcode.run_with_progress(
            transcode.proxy_command(src, out / "proxy.mp4", settings.ffmpeg, settings.x264_preset),
            info.duration_s,
            rep.fraction,
        )

        rep.stage("thumbnails")
        transcode.poster(src, out / "poster.jpg", min(info.duration_s * 0.1, 60), settings.ffmpeg)
        transcode.thumbnails(src, out, info, settings.ffmpeg)
        q["thumbnails"] = True
        if info.has_audio:
            transcode.sync_audio(src, out / "audio_8k.wav", settings.ffmpeg)

        rep.stage("upload")
        upload_dir(s3, bucket, out, prefix)
        result = {
            "checksum_sha256": checksum,
            "duration_s": info.duration_s,
            "fps": info.fps,
            "width": info.width,
            "height": info.height,
            "codec": info.codec,
            "hls_prefix": prefix + "hls/",
            "proxy_key": prefix + "proxy.mp4",
            "poster_key": prefix + "poster.jpg",
            "quality_report": q,
            "renditions": transcode.ladder(info),
            "audio_key": prefix + "audio_8k.wav" if info.has_audio else None,
        }
        rep.succeed(result)
        log.info("ingest_done", job_id=job_id, duration_s=info.duration_s)
        return result
    except (ProbeError, transcode.TranscodeError) as exc:
        rep.fail(f"video could not be processed: {exc}")
        raise
    except Exception as exc:
        rep.fail(f"{type(exc).__name__}: {exc}")
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _workdir(settings: WorkerSettings) -> str:
    Path(settings.work_dir).mkdir(parents=True, exist_ok=True)
    return settings.work_dir


# ---- link import ----------------------------------------------------------------------------


class UnsafeUrlError(ValueError):
    pass


def check_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.port not in (None, 443):
        raise UnsafeUrlError("only https on the default port")
    for info in socket.getaddrinfo(parts.hostname, 443, proto=socket.IPPROTO_TCP):
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise UnsafeUrlError("private address")


def run_import(
    job_id: str,
    organization_id: str,
    match_id: str,
    asset_id: str,
    bucket: str,
    key: str,
    prefix: str,
    url: str,
    settings: WorkerSettings | None = None,
    reporter: Reporter | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    settings = settings or WorkerSettings()
    rep = reporter or Reporter(
        settings.api_internal_url, settings.internal_token, job_id, IMPORT_STAGES
    )
    work = Path(tempfile.mkdtemp(prefix=f"import-{asset_id}-", dir=_workdir(settings)))
    http = client or httpx.Client(timeout=60, follow_redirects=False)
    try:
        rep.stage("download")
        dst = work / "original"
        current = url
        for _ in range(5):  # follow redirects manually, checking every hop
            check_url(current)
            with http.stream("GET", current) as resp:
                if resp.status_code in (301, 302, 303, 307, 308):
                    current = urljoin(current, resp.headers["location"])
                    continue
                if resp.status_code != 200:
                    raise RuntimeError(f"download failed with HTTP {resp.status_code}")
                ctype = resp.headers.get("content-type", "")
                if not (
                    ctype.startswith("video/")
                    or ctype in ("application/octet-stream", "binary/octet-stream")
                ):
                    raise RuntimeError(f"not a video file ({ctype or 'unknown type'})")
                total = int(resp.headers.get("content-length") or 0)
                size = 0
                with dst.open("wb") as f:
                    for chunk in resp.iter_bytes(4 * 1024 * 1024):
                        size += len(chunk)
                        if size > settings.max_import_bytes:
                            raise RuntimeError("file too large")
                        f.write(chunk)
                        if total:
                            rep.fraction(size / total)
                break
        else:
            raise RuntimeError("too many redirects")
        rep.stage("upload")
        _s3(settings).upload_file(str(dst), bucket, key, Config=TRANSFER)
        result = {"size_bytes": size}
        rep.succeed(result)
        return result
    except Exception as exc:
        rep.fail(str(exc))
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)

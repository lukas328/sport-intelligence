from __future__ import annotations

import json
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pytest

from handball_jobkit import Reporter
from handball_worker import ingest
from handball_worker.config import WorkerSettings
from handball_worker.media import quality, transcode
from handball_worker.media.probe import ProbeError, VideoInfo, parse_probe, probe

FFMPEG = shutil.which("ffmpeg")
needs_ffmpeg = pytest.mark.skipif(FFMPEG is None, reason="ffmpeg not installed")


def info(**kw: Any) -> VideoInfo:
    base = {
        "duration_s": 3600.0,
        "width": 1920,
        "height": 1080,
        "fps": 50.0,
        "codec": "h264",
        "bitrate": 8_000_000,
        "has_audio": True,
    }
    return VideoInfo(**{**base, **kw})


def test_parse_probe() -> None:
    data: dict[str, object] = {
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "hevc",
                "width": 3840,
                "height": 2160,
                "avg_frame_rate": "50/1",
                "side_data_list": [{"rotation": -90}],
            },
            {"codec_type": "audio"},
        ],
        "format": {"duration": "3600.5", "bit_rate": "20000000"},
    }
    v = parse_probe(data)
    assert (v.width, v.fps, v.codec, v.has_audio, v.rotation, v.short_side) == (
        3840,
        50.0,
        "hevc",
        True,
        -90,
        2160,
    )
    assert parse_probe(
        {
            "streams": [
                {
                    "codec_type": "video",
                    "width": 1,
                    "height": 1,
                    "r_frame_rate": "30000/1001",
                    "avg_frame_rate": "0/0",
                    "duration": "5",
                }
            ]
        }
    ).fps == pytest.approx(29.97, 0.01)
    with pytest.raises(ProbeError, match="no video"):
        parse_probe({"streams": [{"codec_type": "audio"}], "format": {"duration": "1"}})
    with pytest.raises(ProbeError, match="duration"):
        parse_probe({"streams": [{"codec_type": "video", "width": 1, "height": 1}], "format": {}})


def test_quality_rules() -> None:
    assert quality.check_resolution(info()).level == "ok"
    assert quality.check_resolution(info(width=1280, height=720)).tip == "resolution_low"
    assert quality.check_resolution(info(width=640, height=360)).level == "fail"
    assert quality.check_fps(info(fps=25)).level == "warn"
    assert quality.check_fps(info(fps=15)).level == "fail"
    assert quality.check_duration(info(duration_s=60)).tip == "duration_short"


def _textured(n: int, brightness: float, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    base = rng.integers(0, 60, size=(90, 160)).astype(np.float32) + brightness
    return np.clip(np.stack([base] * n), 0, 255).astype(np.uint8)


def by_id(checks: list[quality.Check]) -> dict[str, quality.Check]:
    return {c.id: c for c in checks}


def test_quality_frames_good_dark_flicker_motion() -> None:
    good = by_id(quality.analyse_windows([_textured(12, 100)]))
    assert good["exposure"].level == "ok"
    assert good["flicker"].level == "ok"
    assert good["camera_motion"].level == "ok"
    assert good["sharpness"].level == "ok"
    assert good["field_visible"].level == "not_evaluated"

    assert by_id(quality.analyse_windows([_textured(12, 0)]))["exposure"].tip == "too_dark"

    flick = _textured(12, 100).astype(np.int16)
    flick[::2] += 12
    assert (
        by_id(quality.analyse_windows([np.clip(flick, 0, 255).astype(np.uint8)]))["flicker"].level
        != "ok"
    )

    moving = np.stack([np.roll(_textured(1, 100)[0], 8 * i, axis=1) for i in range(12)])
    assert by_id(quality.analyse_windows([moving]))["camera_motion"].tip == "camera_moving"

    blurry = np.full((12, 90, 160), 120, dtype=np.uint8)
    assert by_id(quality.analyse_windows([blurry]))["sharpness"].tip == "blurry"


def test_report_overall() -> None:
    r = quality.report(info(width=1280, height=720), [quality.Check("exposure", "ok", 100)])
    assert r["overall"] == "warn"
    assert r["source"] == "heuristic"


def test_ladder_and_hls_command(tmp_path: Path) -> None:
    assert transcode.ladder(info(width=3840, height=2160)) == [1080, 720]
    assert transcode.ladder(info(width=1280, height=720)) == [720]
    assert transcode.ladder(info(width=853, height=481)) == [480]
    cmd = transcode.hls_command(Path("in.mp4"), tmp_path, info(), "ffmpeg", "veryfast", 4)
    joined = " ".join(cmd)
    assert "split=2[v0][v1]" in joined
    assert "v:0,a:0,name:1080p v:1,a:1,name:720p" in joined
    assert "-g 200" in joined
    silent = " ".join(
        transcode.hls_command(Path("in.mp4"), tmp_path, info(has_audio=False), "ffmpeg", "fast", 4)
    )
    assert "-c:a" not in silent
    assert transcode._ts(3725.5) == "01:02:05.500"


@pytest.fixture(scope="module")
def sample_video(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if FFMPEG is None:
        pytest.skip("ffmpeg not installed")
    path = tmp_path_factory.mktemp("v") / "sample.mp4"
    subprocess.run(
        [
            FFMPEG,
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=1280x720:rate=50:duration=8",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=8",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path


class FakeS3:
    def __init__(self, root: Path) -> None:
        self.root = root

    def download_file(self, bucket: str, key: str, filename: str, Config: Any = None) -> None:  # noqa: N803
        shutil.copy(self.root / bucket / key, filename)

    def upload_file(
        self,
        filename: str,
        bucket: str,
        key: str,
        Config: Any = None,  # noqa: N803
        ExtraArgs: Any = None,  # noqa: N803
    ) -> None:
        dst = self.root / bucket / key
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(filename, dst)


def recording_reporter(stages: dict[str, float]) -> tuple[Reporter, list[dict[str, Any]]]:
    posts: list[dict[str, Any]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        posts.append(json.loads(req.content))
        return httpx.Response(200, json={})

    rep = Reporter(
        "http://api",
        "t",
        "job-1",
        stages,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    return rep, posts


@needs_ffmpeg
def test_probe_real_file(sample_video: Path) -> None:
    v = probe(sample_video)
    assert (v.width, v.height, round(v.fps), v.has_audio) == (1280, 720, 50, True)
    with pytest.raises(ProbeError):
        probe(sample_video.with_name("missing.mp4"))


@needs_ffmpeg
def test_run_ingest_end_to_end(
    sample_video: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = tmp_path / "s3"
    (store / "videos" / "o/m/a").mkdir(parents=True)
    shutil.copy(sample_video, store / "videos" / "o/m/a/original.mp4")
    monkeypatch.setattr(ingest, "_s3", lambda s: FakeS3(store))
    rep, posts = recording_reporter(ingest.INGEST_STAGES)
    settings = WorkerSettings(work_dir=str(tmp_path / "work"), x264_preset="ultrafast")
    result = ingest.run_ingest(
        "job-1", "o", "m", "a", "videos", "o/m/a/original.mp4", "o/m/a/", settings, rep
    )
    out = store / "videos" / "o/m/a"
    assert (out / "hls" / "master.m3u8").read_text().count("#EXT-X-STREAM-INF") == 1
    assert list((out / "hls" / "720p").glob("seg_*.m4s"))
    assert (out / "hls" / "720p" / "init.mp4").exists()
    assert (out / "proxy.mp4").exists()
    assert probe(out / "proxy.mp4").fps == 25
    assert (out / "poster.jpg").exists()
    assert "thumbs.jpg#xywh=0,0,160,90" in (out / "thumbs.vtt").read_text()
    assert result["width"] == 1280
    assert result["audio_key"] == "o/m/a/audio_8k.wav"
    assert (out / "audio_8k.wav").stat().st_size > 8000 * 2 * 5  # 8 kHz mono 16 bit, 8 s clip
    assert len(result["checksum_sha256"]) == 64
    assert result["quality_report"]["overall"] in ("warn", "fail")  # 8 s clip: duration_short
    assert posts[-1]["status"] == "succeeded"
    assert [
        p["stage"] for p in posts if p.get("stage") and p["status"] == "running" and "stages" in p
    ] == list(ingest.INGEST_STAGES)
    progresses = [p["progress"] for p in posts]
    assert progresses == sorted(progresses)
    assert not list((tmp_path / "work").iterdir())  # temp files cleaned up


@needs_ffmpeg
def test_run_ingest_reports_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = tmp_path / "s3"
    (store / "videos" / "o").mkdir(parents=True)
    (store / "videos" / "o" / "bad.mp4").write_bytes(b"not a video")
    monkeypatch.setattr(ingest, "_s3", lambda s: FakeS3(store))
    rep, posts = recording_reporter(ingest.INGEST_STAGES)
    with pytest.raises(ProbeError):
        ingest.run_ingest(
            "j",
            "o",
            "m",
            "a",
            "videos",
            "o/bad.mp4",
            "o/",
            WorkerSettings(work_dir=str(tmp_path)),
            rep,
        )
    assert posts[-1]["status"] == "failed"
    assert posts[-1]["error"].startswith("video could not be processed")


def test_check_url(monkeypatch: pytest.MonkeyPatch) -> None:
    for bad in ("http://x.ch/a", "https://x.ch:8080/a", "https:///a"):
        with pytest.raises(ingest.UnsafeUrlError):
            ingest.check_url(bad)
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(0, 0, 0, "", ("10.1.2.3", 443))])
    with pytest.raises(ingest.UnsafeUrlError, match="private"):
        ingest.check_url("https://intranet.example/a.mp4")


def test_run_import_follows_safe_redirects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = tmp_path / "s3"
    monkeypatch.setattr(ingest, "_s3", lambda s: FakeS3(store))
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, *a, **k: [
            (0, 0, 0, "", ("10.0.0.5" if host == "evil.example" else "93.184.216.34", 443))
        ],
    )

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/share":
            return httpx.Response(302, headers={"location": "https://cdn.example/file.mp4"})
        if req.url.path == "/evil":
            return httpx.Response(302, headers={"location": "https://evil.example/x.mp4"})
        if req.url.path == "/page":
            return httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html>")
        return httpx.Response(
            200, headers={"content-type": "video/mp4", "content-length": "6"}, content=b"VIDEO!"
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    rep, posts = recording_reporter(ingest.IMPORT_STAGES)
    settings = WorkerSettings(work_dir=str(tmp_path / "w"))
    res = ingest.run_import(
        "j",
        "o",
        "m",
        "a",
        "videos",
        "o/m/a/original.mp4",
        "o/m/a/",
        "https://veo.example/share",
        settings,
        rep,
        client,
    )
    assert res == {"size_bytes": 6}
    assert (store / "videos/o/m/a/original.mp4").read_bytes() == b"VIDEO!"
    assert posts[-1]["status"] == "succeeded"
    for path, msg in (("/evil", "private"), ("/page", "not a video")):
        rep, posts = recording_reporter(ingest.IMPORT_STAGES)
        with pytest.raises(Exception, match=msg):
            ingest.run_import(
                "j",
                "o",
                "m",
                "a",
                "videos",
                "k",
                "p/",
                f"https://veo.example{path}",
                settings,
                rep,
                client,
            )
        assert posts[-1]["status"] == "failed"

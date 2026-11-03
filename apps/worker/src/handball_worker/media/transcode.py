"""ffmpeg commands: HLS ladder, analysis proxy, poster, thumbnail sprite + WebVTT."""

from __future__ import annotations

import math
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from handball_worker.media.probe import VideoInfo

Progress = Callable[[float], None]


class TranscodeError(Exception):
    pass


def ladder(info: VideoInfo) -> list[int]:
    """Output heights: 1080 and 720 when the source allows it (BRIEF 6.2), never upscale."""
    src = info.short_side
    heights = [h for h in (1080, 720) if src >= h]
    return heights or [src - src % 2]


def hls_command(
    src: Path, out: Path, info: VideoInfo, ffmpeg: str, preset: str, segment_s: int
) -> list[str]:
    heights = ladder(info)
    fps = info.fps if 0 < info.fps <= 60 else 50
    gop = max(1, round(fps * segment_s))
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-y",
        "-i",
        str(src),
        "-progress",
        "pipe:1",
        "-nostats",
    ]
    split = f"[0:v]split={len(heights)}" + "".join(f"[v{i}]" for i in range(len(heights)))
    scales = ";".join(f"[v{i}]scale=-2:{h}[v{i}out]" for i, h in enumerate(heights))
    cmd += ["-filter_complex", f"{split};{scales}"]
    for i, h in enumerate(heights):
        rate = {1080: "5000k", 720: "2800k"}.get(h, "2000k")
        cmd += [
            "-map",
            f"[v{i}out]",
            f"-c:v:{i}",
            "libx264",
            f"-b:v:{i}",
            rate,
            f"-maxrate:v:{i}",
            rate,
            f"-bufsize:v:{i}",
            rate.replace("k", "") + "0k",
        ]
        if info.has_audio:
            cmd += ["-map", "0:a:0"]
    cmd += [
        "-preset",
        preset,
        "-profile:v",
        "high",
        "-pix_fmt",
        "yuv420p",
        "-g",
        str(gop),
        "-keyint_min",
        str(gop),
        "-sc_threshold",
        "0",
    ]
    if info.has_audio:
        cmd += ["-c:a", "aac", "-b:a", "128k", "-ac", "2"]
    streams = " ".join(
        f"v:{i},a:{i},name:{h}p" if info.has_audio else f"v:{i},name:{h}p"
        for i, h in enumerate(heights)
    )
    cmd += [
        "-f",
        "hls",
        "-hls_time",
        str(segment_s),
        "-hls_playlist_type",
        "vod",
        "-hls_segment_type",
        "fmp4",
        "-hls_flags",
        "independent_segments",
        "-master_pl_name",
        "master.m3u8",
        "-var_stream_map",
        streams,
        "-hls_fmp4_init_filename",
        "init.mp4",
        "-hls_segment_filename",
        str(out / "%v" / "seg_%05d.m4s"),
        str(out / "%v" / "index.m3u8"),
    ]
    return cmd


def proxy_command(src: Path, dst: Path, ffmpeg: str, preset: str) -> list[str]:
    """Analysis proxy: 1280 px wide, 25 fps, no audio (BRIEF 6.3 point 4)."""
    return [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-y",
        "-i",
        str(src),
        "-progress",
        "pipe:1",
        "-nostats",
        "-vf",
        "scale=1280:-2,fps=25",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        "26",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(dst),
    ]


def run_with_progress(
    cmd: list[str], duration_s: float, on_progress: Progress | None = None
) -> None:
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.stdout is not None
    for line in proc.stdout:
        m = re.match(r"out_time_us=(\d+)", line.strip())
        if m and on_progress and duration_s > 0:
            on_progress(min(1.0, int(m.group(1)) / 1e6 / duration_s))
    _, err = proc.communicate()
    if proc.returncode != 0:
        raise TranscodeError(err.strip().splitlines()[-1] if err.strip() else "ffmpeg failed")


AUDIO_SYNC_S = 600


def sync_audio(src: Path, dst: Path, ffmpeg: str, seconds: int = AUDIO_SYNC_S) -> None:
    """First minutes of audio as 8 kHz mono WAV (about 1 MB per minute) for camera sync."""
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-y",
            "-i",
            str(src),
            "-t",
            str(seconds),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "8000",
            "-c:a",
            "pcm_s16le",
            str(dst),
        ],
        check=True,
        capture_output=True,
        timeout=300,
    )


def poster(src: Path, dst: Path, at_s: float, ffmpeg: str) -> None:
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-y",
            "-ss",
            f"{at_s:.2f}",
            "-i",
            str(src),
            "-frames:v",
            "1",
            "-vf",
            "scale=1280:-2",
            "-q:v",
            "4",
            str(dst),
        ],
        check=True,
        capture_output=True,
        timeout=120,
    )


def thumbnails(
    src: Path,
    out_dir: Path,
    info: VideoInfo,
    ffmpeg: str,
    every_s: int = 10,
    width: int = 160,
    cols: int = 10,
) -> tuple[Path, Path]:
    """Sprite sheet + WebVTT for timeline hover previews."""
    count = max(1, math.ceil(info.duration_s / every_s))
    rows = math.ceil(count / cols)
    height = round(width * info.height / info.width / 2) * 2 if info.width else 90
    sprite = out_dir / "thumbs.jpg"
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-y",
            "-i",
            str(src),
            "-vf",
            f"fps=1/{every_s},scale={width}:{height},tile={cols}x{rows}",
            "-frames:v",
            "1",
            "-q:v",
            "6",
            str(sprite),
        ],
        check=True,
        capture_output=True,
        timeout=1800,
    )
    lines = ["WEBVTT", ""]
    for i in range(count):
        start, end = i * every_s, min((i + 1) * every_s, info.duration_s)
        x, y = (i % cols) * width, (i // cols) * height
        lines += [f"{_ts(start)} --> {_ts(end)}", f"thumbs.jpg#xywh={x},{y},{width},{height}", ""]
    vtt = out_dir / "thumbs.vtt"
    vtt.write_text("\n".join(lines))
    return sprite, vtt


def _ts(s: float) -> str:
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{sec:06.3f}"


def sample_gray_frames(
    src: Path,
    info: VideoInfo,
    ffmpeg: str,
    n_windows: int = 6,
    frames_per_window: int = 12,
    width: int = 320,
) -> list[NDArray[np.uint8]]:
    """Grayscale frame samples from several windows across the video (stream-decoded, no files)."""
    height = round(width * info.height / info.width / 2) * 2 if info.width else 180
    rate = 10.0
    chunks = []
    for k in range(n_windows):
        start = info.duration_s * (k + 0.5) / n_windows
        proc = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-nostdin",
                "-ss",
                f"{start:.2f}",
                "-i",
                str(src),
                "-frames:v",
                str(frames_per_window),
                "-vf",
                f"fps={rate},scale={width}:{height}",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "gray",
                "pipe:1",
            ],
            capture_output=True,
            timeout=300,
            check=False,
        )
        buf = np.frombuffer(proc.stdout, dtype=np.uint8)
        n = len(buf) // (width * height)
        if n:
            chunks.append(buf[: n * width * height].reshape(n, height, width))
    if not chunks:
        raise TranscodeError("could not decode frames")
    return chunks

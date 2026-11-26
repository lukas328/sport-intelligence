"""ffmpeg commands: HLS ladder, analysis proxy, poster, thumbnail sprite + WebVTT."""

from __future__ import annotations

import math
import re
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

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
    src: Path,
    out: Path,
    info: VideoInfo,
    ffmpeg: str,
    preset: str,
    segment_s: int,
    proxy: Path | None = None,
) -> list[str]:
    """The HLS ladder; with `proxy` the analysis proxy comes out of the same run, with one decode
    of the source for all outputs. Measured 26.11.2026 on one CPU core, 120 s of 1080p50 at
    15 Mbit/s: 419 s as two runs (HLS 323 s, proxy 97 s), 371 s as one (-11 %), same files."""
    heights = ladder(info)
    fps = info.fps if 0 < info.fps <= 60 else 50
    gop = max(1, round(fps * segment_s))
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(src),
    ]
    # every file gets a sound track, a silent one when it has none: the files of one match (two
    # halves) are then built alike and play across the break as one video (Q-VIDEO-PARTS)
    if not info.has_audio:
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
    cmd += ["-progress", "pipe:1", "-nostats"]
    audio = "0:a:0" if info.has_audio else "1:a:0"
    n = len(heights) + (1 if proxy else 0)
    split = f"[0:v]split={n}" + "".join(f"[v{i}]" for i in range(n))
    scales = ";".join(f"[v{i}]scale=-2:{h}[v{i}out]" for i, h in enumerate(heights))
    if proxy:
        scales += f";[v{len(heights)}]{PROXY_FILTER}[proxy]"
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
        cmd += ["-map", audio]
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
    cmd += ["-c:a", "aac", "-b:a", "128k", "-ac", "2"]
    if not info.has_audio:
        cmd += ["-shortest"]  # the silent track ends with the picture
    streams = " ".join(f"v:{i},a:{i},name:{h}p" for i, h in enumerate(heights))
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
    if proxy:
        cmd += ["-map", "[proxy]", "-an", *_proxy_codec(preset), str(proxy)]
    return cmd


# the analysis proxy: 1280 px wide, 25 fps, no audio (BRIEF 6.3 point 4)
PROXY_FILTER = "scale=1280:-2,fps=25"


def _proxy_codec(preset: str) -> list[str]:
    return [
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
    ]


def proxy_command(src: Path, dst: Path, ffmpeg: str, preset: str) -> list[str]:
    """Analysis proxy: 1280 px wide, 25 fps, no audio (BRIEF 6.3 point 4)."""
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(src),
        "-progress",
        "pipe:1",
        "-nostats",
        "-vf",
        PROXY_FILTER,
        "-an",
        *_proxy_codec(preset),
        str(dst),
    ]


def run_with_progress(
    cmd: list[str], duration_s: float, on_progress: Progress | None = None
) -> None:
    """Run ffmpeg, reading `-progress pipe:1` from stdout. stderr goes to a temporary file, not a
    pipe: a pipe nobody reads fills up on a long run and blocks ffmpeg (deadlock)."""
    with tempfile.TemporaryFile(mode="w+") as errfile:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errfile, text=True)
        assert proc.stdout is not None
        for line in proc.stdout:
            m = re.match(r"out_time_us=(\d+)", line.strip())
            if m and on_progress and duration_s > 0:
                on_progress(min(1.0, int(m.group(1)) / 1e6 / duration_s))
        proc.wait()
        errfile.seek(0)
        err = errfile.read().strip()
    if proc.returncode != 0:
        raise TranscodeError(err.splitlines()[-1] if err else "ffmpeg failed")


# the sound track of the whole video, mono 16 kHz WAV (32 kB per second: about 115 MB for 60 min,
# 190 MB for 99 min). Camera sync reads its first minutes (handball_vision.audio.load_mono resamples
# to 8 kHz); the analysis listens for whistles, whose fundamental lies at 3.7 to 4.1 kHz: at 8 kHz
# (Nyquist 4 kHz) the whistle detection reached F1 0.69, at 16 kHz 0.83 (analysis, 26.11.2026).
# Until then the file was audio_8k.wav with the first 600 s only; readers take the key the asset
# stores (audio_key), so old and new files both work.
AUDIO_SR = 16_000
AUDIO_FILE = "audio_16k.wav"
# a file whose loudest sample stays below this is silent (16-bit full scale is 32767)
SILENT_PEAK = 8


class AudioSummary(TypedDict):
    seconds: float
    silent: bool


def extract_audio(src: Path, dst: Path, ffmpeg: str, duration_s: float = 0.0) -> AudioSummary:
    """The first audio stream of the whole video as mono 16 kHz WAV; returns its length and
    whether it is silent (a stream without any sound, as the Uznach upload of 26.11.2026: the
    source's own track was digital silence, -inf dB on both channels)."""
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-y",
            "-i",
            str(src),
            # the first audio stream, as load_mono decodes it (ffmpeg would pick the one with the
            # most channels)
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(AUDIO_SR),
            "-c:a",
            "pcm_s16le",
            str(dst),
        ],
        check=True,
        capture_output=True,
        # demuxing a long file takes a while: a minute plus a second per 10 s of video
        timeout=max(300, int(60 + duration_s / 10)),
    )
    return audio_summary(dst)


def audio_summary(wav: Path) -> AudioSummary:
    """Length in seconds and «silent» of a mono 16-bit WAV, read in blocks (no full load)."""
    import wave

    peak = 0
    with wave.open(str(wav), "rb") as w:
        rate, frames = w.getframerate(), w.getnframes()
        while True:
            block = w.readframes(1 << 20)
            if not block:
                break
            a = np.frombuffer(block, "<i2")
            if len(a):
                peak = max(peak, int(np.abs(a.astype(np.int32)).max()))
    return {"seconds": round(frames / rate, 2) if rate else 0.0, "silent": peak < SILENT_PEAK}


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

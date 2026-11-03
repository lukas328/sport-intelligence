"""ffprobe wrapper."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


class ProbeError(Exception):
    pass


@dataclass(frozen=True)
class VideoInfo:
    duration_s: float
    width: int
    height: int
    fps: float
    codec: str
    bitrate: int | None
    has_audio: bool
    rotation: int = 0
    recorded_at: str | None = None  # creation_time from the file metadata (camera clock)

    @property
    def short_side(self) -> int:
        return min(self.width, self.height)


def _fps(rate: str | None) -> float:
    if not rate or rate in ("0/0", "0"):
        return 0.0
    try:
        return float(Fraction(rate))
    except (ValueError, ZeroDivisionError):
        return 0.0


def parse_probe(data: dict[str, object]) -> VideoInfo:
    streams = data.get("streams") or []
    assert isinstance(streams, list)
    video = next(
        (s for s in streams if isinstance(s, dict) and s.get("codec_type") == "video"), None
    )
    if video is None:
        raise ProbeError("no video stream")
    fmt = data.get("format") or {}
    assert isinstance(fmt, dict)
    duration = float(video.get("duration") or fmt.get("duration") or 0)
    if duration <= 0:
        raise ProbeError("unknown duration")
    rotation = 0
    for side in video.get("side_data_list") or []:
        if isinstance(side, dict) and "rotation" in side:
            rotation = int(side["rotation"])
    bitrate = fmt.get("bit_rate")
    return VideoInfo(
        duration_s=duration,
        width=int(video["width"]),
        height=int(video["height"]),
        fps=_fps(str(video.get("avg_frame_rate"))) or _fps(str(video.get("r_frame_rate"))),
        codec=str(video.get("codec_name", "unknown")),
        bitrate=int(str(bitrate)) if bitrate else None,
        has_audio=any(isinstance(s, dict) and s.get("codec_type") == "audio" for s in streams),
        rotation=rotation,
        recorded_at=_creation_time(fmt, video),
    )


def _creation_time(fmt: dict[str, object], video: dict[str, object]) -> str | None:
    for src in (fmt, video):
        tags = src.get("tags")
        if isinstance(tags, dict):
            value = tags.get("creation_time") or tags.get("com.apple.quicktime.creationdate")
            if isinstance(value, str) and len(value) >= 19:
                return value
    return None


def probe(path: Path, ffprobe: str = "ffprobe") -> VideoInfo:
    proc = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        raise ProbeError(proc.stderr.strip()[:500] or "ffprobe failed")
    return parse_probe(json.loads(proc.stdout))

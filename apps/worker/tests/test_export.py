"""Presentation MP4 export (addendum 01, 4.1): planning, drawings and a real ffmpeg render."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from handball_worker.config import WorkerSettings
from handball_worker.export import draw_shapes, plan_clip, render


def test_plan_clip_with_slow_motion_and_holds() -> None:
    slide = {
        "in_ms": 10_000,
        "out_ms": 20_000,
        "slow": [{"from_ms": 12_000, "to_ms": 14_000, "rate": 0.5}],
        "holds": [{"t_ms": 15_000, "duration_ms": 3000, "shapes": []}],
    }
    assert plan_clip(slide) == [
        ("play", 10.0, 12.0, 1.0),
        ("play", 12.0, 14.0, 0.5),
        ("play", 14.0, 15.0, 1.0),
        ("hold", 15.0, 3.0, 0.0),
        ("play", 15.0, 20.0, 1.0),
    ]


def test_draw_shapes_changes_pixels() -> None:
    img = Image.new("RGB", (200, 100), (0, 0, 0))
    out = draw_shapes(
        img,
        [
            {"kind": "arrow", "points": [[0.1, 0.5], [0.9, 0.5]], "color": "#ffd200", "width": 4},
            {
                "kind": "spotlight",
                "points": [[0.5, 0.5], [0.6, 0.5]],
                "color": "#ffffff",
                "width": 2,
            },
            {"kind": "circle", "points": [[0.1, 0.1], [0.3, 0.3]], "color": "#ff0000", "width": 2},
            {"kind": "text", "points": [[0.05, 0.8]], "color": "#00ff00", "width": 2, "text": "7"},
        ],
    )
    assert out.getpixel((100, 50)) != (0, 0, 0)
    assert out.size == (200, 100)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_render_concatenates_pieces(tmp_path: Path) -> None:
    src = tmp_path / "proxy.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x180:rate=25:duration=6",
            "-pix_fmt",
            "yuv420p",
            str(src),
        ],
        check=True,
        capture_output=True,
    )
    settings = WorkerSettings(ffmpeg="ffmpeg")
    slides: list[dict[str, Any]] = [
        {"type": "text", "lines": ["Video-Sitzung", "Rückzug"]},
        {
            "type": "clip",
            "video_id": "v1",
            "in_ms": 1000,
            "out_ms": 3000,
            "slow": [{"from_ms": 1500, "to_ms": 2000, "rate": 0.5}],
            "holds": [
                {
                    "t_ms": 2500,
                    "duration_ms": 1000,
                    "shapes": [
                        {
                            "kind": "arrow",
                            "points": [[0.1, 0.1], [0.5, 0.5]],
                            "color": "#ffd200",
                            "width": 4,
                        }
                    ],
                }
            ],
        },
    ]
    out = render(settings, slides, {"v1": src}, tmp_path)
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=width,height",
            "-of",
            "json",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    info = json.loads(probe.stdout)
    assert info["streams"][0]["width"] == 1280
    # 4 s card + 0.5 + 1.0 (slow) + 0.5 + 1.0 hold + 0.5
    assert 7.0 < float(info["format"]["duration"]) < 8.3


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_spotlight_pieces_use_the_reel_renderer(tmp_path: Path) -> None:
    import numpy as np

    from handball_vision.synthetic import SyntheticConfig, SyntheticMatch
    from handball_worker import reels

    match = SyntheticMatch(SyntheticConfig(seconds=4, noise=0))
    src = tmp_path / "proxy.mp4"
    truth = match.write(src)
    rows = np.array(
        [[f.t_ms, o.object_id, o.x, o.y] for f in truth for o in f.objects if o.label != "ball"],
        dtype=np.float32,
    )
    settings = WorkerSettings(ffmpeg="ffmpeg")
    calls: list[tuple[float, float]] = []

    def piece(slide: dict[str, Any], s: Path, x: float, y: float, out: Path) -> bool:
        calls.append((x, y))
        ctx = {
            "format": "16x9",
            "homography": match.h.tolist(),
            "image_size": [1280, 720],
            "player_tracks": [],
        }
        reels.render_clip(
            settings,
            s,
            {"in_ms": round(x * 1000), "out_ms": round(y * 1000), "spotlight_track": 1},
            rows,
            ctx,
            out,
        )
        return True

    slides: list[dict[str, Any]] = [
        {
            "type": "clip",
            "video_id": "v1",
            "in_ms": 500,
            "out_ms": 2500,
            "spotlight": [1],
            "slow": [{"from_ms": 1500, "to_ms": 2500, "rate": 0.5}],
        }
    ]
    out = render(settings, slides, {"v1": src}, tmp_path, piece)
    assert calls == [(0.5, 1.5), (1.5, 2.5)]
    duration = float(
        subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(out),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert 2.7 < duration < 3.4  # 1 s normal + 1 s at half speed

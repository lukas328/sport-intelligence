"""Presentation MP4 export (addendum 01, 4.1): planning, drawings and a real ffmpeg render."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

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
    slides = [
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

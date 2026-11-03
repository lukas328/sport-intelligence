"""Highlight reels (addendum 01, 4.3)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from handball_worker.config import WorkerSettings
from handball_worker.reels import crop_path, render_local


def test_crop_follows_the_players() -> None:
    h: list[list[float]] = [[32.0, 0, 0], [0, 36.0, 0], [0, 0, 1]]  # 40 x 20 m -> 1280 x 720 px
    rows = np.array(
        [[t, tid, 34.0 + tid * 0.2, 10.0] for t in range(0, 4000, 40) for tid in range(1, 7)],
        dtype=np.float32,
    )
    lefts = crop_path(rows, list(range(0, 4000, 40)), h, (1280, 720), {1, 2, 3, 4, 5, 6}, 405)
    assert all(
        left == 1280 - 405 for left in lefts
    )  # play at the right goal: crop at the right edge
    empty = crop_path(np.zeros((0, 4), np.float32), [0, 40], None, (1280, 720), set(), 405)
    assert empty == [int(640 - 405 / 2)] * 2


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_render_portrait_reel(tmp_path: Path) -> None:
    from handball_vision.synthetic import SyntheticConfig, SyntheticMatch

    cfg = SyntheticConfig(seconds=6, noise=0)
    match = SyntheticMatch(cfg)
    src = tmp_path / "proxy.mp4"
    truth = match.write(src)
    rows = np.array(
        [[f.t_ms, o.object_id, o.x, o.y] for f in truth for o in f.objects if o.label != "ball"],
        dtype=np.float32,
    )
    payload: dict[str, Any] = {
        "format": "9x16",
        "intro": ["HC Test", "HC Test - TV Gegner", "25:23"],
        "colour": "#0b6bcb",
        "homography": match.h.tolist(),
        "image_size": [1280, 720],
        "player_tracks": [
            o.object_id for o in truth[0].objects if o.label not in ("ball", "referee")
        ],
        "clips": [{"in_ms": 1000, "out_ms": 4000, "label": "#7 Lena", "spotlight_track": 1}],
    }
    out = render_local(WorkerSettings(ffmpeg="ffmpeg"), payload, src, rows, None, tmp_path)
    info = json.loads(
        subprocess.run(
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
        ).stdout
    )
    assert (info["streams"][0]["width"], info["streams"][0]["height"]) == (720, 1280)
    assert 5.5 < float(info["format"]["duration"]) < 6.6  # 3 s intro + 3 s scene

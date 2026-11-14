"""Highlight reels (addendum 01, 4.3)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import ImageFont

from handball_worker import reels
from handball_worker.config import WorkerSettings
from handball_worker.export import FFMPEG_TIMEOUT_S
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


def _hanging_ffmpeg(tmp_path: Path) -> str:
    script = tmp_path / "fake-ffmpeg"
    script.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(30)\n")
    script.chmod(0o755)
    return str(script)


def test_render_clip_stops_a_hanging_ffmpeg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(reels, "FFMPEG_TIMEOUT_S", 0.5)
    settings = WorkerSettings(ffmpeg=_hanging_ffmpeg(tmp_path))
    clip = {"in_ms": 0, "out_ms": 1000, "label": ""}
    ctx: dict[str, Any] = {"format": "16x9", "player_tracks": []}
    started = time.monotonic()
    with pytest.raises(RuntimeError, match="timed out"):
        reels.render_clip(
            settings,
            tmp_path / "in.mp4",
            clip,
            np.zeros((0, 4), np.float32),
            ctx,
            tmp_path / "o.mp4",
        )
    assert time.monotonic() - started < 10


def test_reel_ffmpeg_calls_have_a_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    timeouts: list[float | None] = []

    def fake_run(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess[bytes]:
        timeouts.append(kw.get("timeout"))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(reels, "render_clip", lambda *a, **kw: None)
    payload: dict[str, Any] = {"format": "16x9", "clips": [{"in_ms": 0, "out_ms": 1000}]}
    render_local(
        WorkerSettings(), payload, tmp_path / "in.mp4", np.zeros((0, 4), np.float32), None, tmp_path
    )
    assert timeouts == [FFMPEG_TIMEOUT_S, FFMPEG_TIMEOUT_S]


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_reel_of_a_match_in_two_files(tmp_path: Path) -> None:
    """Each clip is cut from the file of its half, at its time in that file (Q-VIDEO-PARTS)."""
    first, second = tmp_path / "a.mp4", tmp_path / "b.mp4"
    for path, dur in ((first, 4), (second, 6)):
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"testsrc2=size=1280x720:rate=25:duration={dur}",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                str(path),
            ],
            check=True,
        )
    rows = np.zeros((0, 4), np.float32)
    payload: dict[str, Any] = {
        "format": "16x9",
        "intro": ["HC Test"],
        "colour": "#0b6bcb",
        "player_tracks": [],
        "clips": [
            {"in_ms": 0, "out_ms": 2000, "label": "", "spotlight_track": None, "source": 0},
            # 4.5 s into the second file: past the end of the first one
            {"in_ms": 4500, "out_ms": 5500, "label": "", "spotlight_track": None, "source": 1},
        ],
    }
    files = [(first, rows, {**payload, "player_tracks": []}), (second, rows, {**payload})]
    out = reels.render_local(
        WorkerSettings(ffmpeg="ffmpeg"), payload, first, rows, None, tmp_path, files
    )
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
    assert 5.5 < duration < 6.6  # 3 s intro + 2 s + 1 s


def test_title_card_writes_umlauts() -> None:
    """Echtlauf 5 P8: «SG Wädenswil/Horgen - Lakers Stäfa» came out as «W?denswil … St?fa»
    (Pillow's built-in font has no umlauts). The card uses the app's own typeface, shipped with
    the worker."""
    face = reels.font(40)
    assert reels.FONT.is_file() and isinstance(face, ImageFont.FreeTypeFont)
    missing = face.getmask("￿").getbbox()  # what a glyph the font lacks looks like
    for ch in "äöüéÄÖÜè":
        assert face.getmask(ch).getbbox() != missing, ch
    card = reels.intro_card(["SG Wädenswil/Horgen - Lakers Stäfa"], "#d3202e", None, (640, 360))
    assert card.size == (640, 360)

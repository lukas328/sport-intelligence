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
    times = list(range(0, 4000, 40))
    where = reels.places({"homography": h, "image_size": [1280, 720]}, times)
    lefts = crop_path(rows, times, where, {1, 2, 3, 4, 5, 6}, 405)
    assert all(
        left == 1280 - 405 for left in lefts
    )  # play at the right goal: crop at the right edge
    empty = crop_path(np.zeros((0, 4), np.float32), [0, 40], [None, None], set(), 405)
    assert empty == [int(640 - 405 / 2)] * 2


# a moving camera (ADR 020): the court maps onto the hall image, 20 px per metre from (100, 50);
# the camera turns so the hall moves 8 px to the left per frame
COURT: list[list[float]] = [[20.0, 0, 100], [0, 20.0, 50], [0, 0, 1]]


def _turned(dx: float) -> list[float]:
    return [1.0, 0, -dx, 0, 1.0, 0, 0, 0, 1.0]


def _views(times: list[int], step: float = 0.2) -> np.ndarray[Any, np.dtype[np.float32]]:
    return np.array([[t, *_turned(t * step)] for t in times], np.float32)


def test_view_at_interpolates_and_leaves_gaps() -> None:
    views = _views([0, 40, 80, 400])
    v = reels.view_at(views, 60)
    assert v is not None and v[0, 2] == pytest.approx(-12)  # between -8 and -16
    assert reels.view_at(views, 240) is None  # 80 .. 400 not placed: nothing drawn
    near = reels.view_at(views, 110)
    assert near is not None and near[0, 2] == pytest.approx(-16)
    assert reels.view_at(np.zeros((0, 10), np.float32), 0) is None


def test_places_follow_a_moving_camera() -> None:
    times = [0, 40, 1000]
    ctx: dict[str, Any] = {
        "homography": COURT,
        "image_size": [1800, 400],
        "frame_size": [1280, 720],
        "views": _views([0, 40]),
    }
    where = reels.places(ctx, times)
    assert where[2] is None  # no view there
    first, second = where[0], where[1]
    assert first is not None and second is not None
    assert first[1] == second[1] == (1280, 720)
    # the centre spot (20, 10) is at hall px (500, 250): at 40 ms the camera turned 8 px
    assert reels.project(first[0], np.array([[20.0, 10.0]]))[0] == pytest.approx([500, 250])
    assert reels.project(second[0], np.array([[20.0, 10.0]]))[0] == pytest.approx([492, 250])
    ring = reels.spotlight_at(np.array([[40, 7, 20.0, 10.0]], np.float32), 7, 40, *second)
    assert ring == pytest.approx((492, 250))
    # a fixed camera: its calibration for every frame; no court: nothing
    fixed = reels.places({"homography": COURT, "image_size": [1280, 720]}, times)
    assert fixed == [(COURT, (1280, 720))] * 3
    assert reels.places({}, times) == [None] * 3


def test_crop_keeps_its_place_where_the_camera_is_unknown() -> None:
    times = [0, 40, 80]
    rows = np.array([[t, 1, 50.0, 10.0] for t in times], np.float32)  # 1100 px on the hall image
    ctx: dict[str, Any] = {
        "homography": COURT,
        "image_size": [1800, 400],
        "frame_size": [1280, 720],
        "views": _views([0, 40], step=10),  # turned 400 px at 40 ms
    }
    lefts = crop_path(rows, times, reels.places(ctx, times), {1}, 405)
    # the player on the frame: 1100 px, then 700 px as the camera turned; at 80 ms the view is
    # unknown and the crop stays at 700 px instead of jumping to the middle (smoothed over 3)
    assert lefts == [764, 630, 497]


class _S3:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.asked: list[str] = []

    def download_file(self, bucket: str, key: str, dst: str) -> None:
        self.asked.append(key)
        if key not in self.files:
            raise FileNotFoundError(key)
        Path(dst).write_bytes(self.files[key])


def test_with_views_loads_what_the_clips_need(tmp_path: Path) -> None:
    ctx: dict[str, Any] = {
        "homography": COURT,
        "image_size": [1800, 400],
        "chunks_prefix": "o/m/v/analysis/",
        "chunk_ms": 30_000,
        "view_chunks": 2,
        "frame_size": [1280, 720],
    }
    s3 = _S3({"o/m/v/analysis/view_00001.bin": _views([30_000, 30_040]).tobytes()})
    clips = [{"in_ms": 31_000, "out_ms": 70_000}]  # chunk 2 does not exist: never asked
    out = reels.with_views(s3, "art", ctx, clips, tmp_path)
    assert s3.asked == ["o/m/v/analysis/view_00001.bin"]
    assert out["views"].shape == (2, 10) and out["views"][0, 0] == 30_000
    # a fixed camera, or a moving one without view files: the context as it is
    assert reels.with_views(s3, "art", {**ctx, "view_chunks": None}, clips, tmp_path) == {
        **ctx,
        "view_chunks": None,
    }
    # view files not found: an empty table, so nothing is drawn
    gone = reels.with_views(_S3({}), "art", ctx, clips, tmp_path)
    assert gone["views"].shape == (0, 10)
    assert reels.places(gone, [31_000]) == [None]


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
    """Echtlauf 5 P8: «SG Lärchenwil/Kalvenegg - Seehasen Sälmatt» came out as
    «L?rchenwil … S?lmatt» (Pillow's built-in font has no umlauts). The card uses the app's own
    typeface, shipped with the worker."""
    face = reels.font(40)
    assert reels.FONT.is_file() and isinstance(face, ImageFont.FreeTypeFont)
    missing = face.getmask("￿").getbbox()  # what a glyph the font lacks looks like
    for ch in "äöüéÄÖÜè":
        assert face.getmask(ch).getbbox() != missing, ch
    card = reels.intro_card(
        ["SG Lärchenwil/Kalvenegg - Seehasen Sälmatt"], "#d3202e", None, (640, 360)
    )
    assert card.size == (640, 360)


def _yellow_near(path: Path, at_s: float, x: int, y: int, r: int = 6) -> bool:
    raw = subprocess.run(
        [
            *("ffmpeg", "-v", "error", "-ss", f"{at_s}", "-i", str(path), "-frames:v", "1"),
            *("-f", "rawvideo", "-pix_fmt", "rgb24", "-"),
        ],
        check=True,
        capture_output=True,
    ).stdout
    img = np.frombuffer(raw, np.uint8).reshape(720, 1280, 3).astype(int)
    patch = img[y - r : y + r, x - r : x + r]
    return bool(((patch[..., 0] > 170) & (patch[..., 1] > 140) & (patch[..., 2] < 120)).any())


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_the_burned_in_ring_follows_a_moving_camera(tmp_path: Path) -> None:
    src = tmp_path / "grey.mp4"
    subprocess.run(
        [
            *("ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=1280x720:d=2:r=25"),
            *("-pix_fmt", "yuv420p", str(src)),
        ],
        check=True,
    )
    times = list(range(0, 2000, 40))
    rows = np.array([[t, 7, 20.0, 10.0] for t in times], np.float32)  # standing on the centre spot
    ctx: dict[str, Any] = {
        "format": "16x9",
        "player_tracks": [],
        "homography": COURT,
        "image_size": [1800, 400],
        "frame_size": [1280, 720],
        "views": _views(times),  # 0.2 px per ms: 200 px turned after 1 s
    }
    clip = {"in_ms": 0, "out_ms": 2000, "label": "", "spotlight_track": 7}
    out = tmp_path / "o.mp4"
    reels.render_clip(WorkerSettings(ffmpeg="ffmpeg"), src, clip, rows, ctx, out)
    rx = round(1280 * 0.03)
    # the centre spot is at hall px (500, 250); after 1 s the camera turned 200 px: frame x 300
    assert _yellow_near(out, 1.0, 300 - rx, 250)
    assert not _yellow_near(out, 1.0, 500 - rx, 250)  # not where the hall image would put it

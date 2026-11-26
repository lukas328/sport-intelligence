"""Highlight reels (addendum 01, 4.3): intro card, scenes in 16:9 or 9:16, crop that follows the
play, burned-in spotlight and a name strip. Frames are processed in Python between an ffmpeg
decoder and encoder (raw RGB pipes); no music (licences), a hook for a licence-free library can
add an audio track later.
"""

from __future__ import annotations

import contextlib
import io
import subprocess
import threading
from pathlib import Path
from typing import IO, Any

import numpy as np
import structlog
from numpy.typing import NDArray
from PIL import Image, ImageDraw, ImageFont

from handball_worker.artifacts import run_artifact_job
from handball_worker.config import WorkerSettings
from handball_worker.export import ENC, FFMPEG_TIMEOUT_S, FPS

log = structlog.get_logger("worker.reels")
SRC_W, SRC_H = 1280, 720
INTRO_S = 3.0
SMOOTH_FRAMES = 37  # 1.5 s moving average: the crop pans calmly
FrameArray = NDArray[np.uint8]


def project(
    h: list[list[float]] | NDArray[np.float64], xy: NDArray[np.float64]
) -> NDArray[np.float64]:
    pts = np.c_[xy, np.ones(len(xy))] @ np.asarray(h, dtype=np.float64).T
    out: NDArray[np.float64] = pts[:, :2] / pts[:, 2:3]
    return out


Homography = list[list[float]] | NDArray[np.float64]
# court -> picture of one frame and the image size it maps into; None: not known for that frame
Place = tuple[Homography, tuple[int, int]]
VIEW_ROW = 10  # view files: float32 [t_ms, h00 .. h22]
VIEW_SPAN_MS = 100  # neighbouring view samples further apart are a gap (as in the web player)
VIEW_NEAR_MS = 50


def view_at(views: NDArray[np.float32], t: float) -> NDArray[np.float64] | None:
    """Hall image -> frame of a moving camera at time t (ADR 020): interpolated between two
    neighbouring frames, the nearest frame close by, else None (a gap: nothing is drawn)."""
    if not len(views):
        return None
    ts = views[:, 0]
    j = int(np.searchsorted(ts, t, side="right"))  # first row after t
    i = j - 1
    ti = float(ts[i]) if i >= 0 else -np.inf
    tj = float(ts[j]) if j < len(views) else np.inf
    if i >= 0 and j < len(views) and tj - ti <= VIEW_SPAN_MS:
        f = (t - ti) / (tj - ti) if tj > ti else 0.0
        a = views[i, 1:].astype(np.float64)
        b = views[j, 1:].astype(np.float64)
        out: NDArray[np.float64] = (a + (b - a) * f).reshape(3, 3)
        return out
    if t - ti <= VIEW_NEAR_MS:
        return np.asarray(views[i, 1:], np.float64).reshape(3, 3)
    if tj - t <= VIEW_NEAR_MS:
        return np.asarray(views[j, 1:], np.float64).reshape(3, 3)
    return None


def places(ctx: dict[str, Any], times_ms: list[int]) -> list[Place | None]:
    """Court -> picture per frame: the calibration itself for a fixed camera; for a moving one
    (view files loaded as `views`) composed with where the camera looked at that moment."""
    h = ctx.get("homography")
    if h is None:
        return [None] * len(times_ms)
    w, hgt = ctx.get("image_size") or (SRC_W, SRC_H)
    size = (int(w), int(hgt))
    views = ctx.get("views")
    if views is None:
        return [(h, size)] * len(times_ms)
    frame = (int(ctx["frame_size"][0]), int(ctx["frame_size"][1]))
    court = np.asarray(h, np.float64)
    out: list[Place | None] = []
    for t in times_ms:
        v = view_at(views, t)
        out.append(None if v is None else (v @ court, frame))
    return out


def crop_path(
    rows: NDArray[np.float32],
    times_ms: list[int],
    where: list[Place | None],
    players: set[int],
    crop_w: int,
) -> list[int]:
    """Left edge of a portrait crop per frame: median of the projected players, smoothed. A
    frame whose court -> picture is not known keeps the crop where it was."""
    centre = SRC_W / 2
    xs: list[float] = []
    for t, place in zip(times_ms, where, strict=True):
        if place is None or len(rows) == 0:
            xs.append(xs[-1] if xs else centre)
            continue
        h, size = place
        sel = rows[(np.abs(rows[:, 0] - t) <= 60) & np.isin(rows[:, 1], list(players))]
        if len(sel) == 0:
            xs.append(xs[-1] if xs else centre)
            continue
        img = project(h, sel[:, 2:4].astype(np.float64))
        scale = SRC_W / size[0]
        xs.append(float(np.median(img[:, 0])) * scale)
    arr = np.array(xs)
    k = min(SMOOTH_FRAMES, len(arr)) or 1
    pad = np.pad(arr, (k // 2, k - 1 - k // 2), mode="edge")
    smooth = np.convolve(pad, np.ones(k) / k, mode="valid")
    return [int(np.clip(c - crop_w / 2, 0, SRC_W - crop_w)) for c in smooth]


def spotlight_at(
    rows: NDArray[np.float32], track: int, t: int, h: Homography, size: tuple[int, int]
) -> tuple[float, float] | None:
    sel = rows[(rows[:, 1] == track) & (np.abs(rows[:, 0] - t) <= 120)]
    if len(sel) == 0:
        return None
    best = sel[np.argmin(np.abs(sel[:, 0] - t))]
    p = project(h, np.array([[best[2], best[3]]], dtype=np.float64))[0]
    return float(p[0] * SRC_W / size[0]), float(p[1] * SRC_H / size[1])


# the app's own typeface (Hanken Grotesk, SIL OFL, licence beside it), shipped with the worker:
# Pillow's built-in font has no umlauts («W?denswil», Echtlauf 5 P8) and the image has no fonts
FONT = Path(__file__).parent / "fonts" / "HankenGrotesk-wght.ttf"


def font(px: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        f = ImageFont.truetype(str(FONT), px)
        with contextlib.suppress(OSError, AttributeError):
            f.set_variation_by_axes([700 if bold else 500])
        return f
    except OSError:  # pragma: no cover - the file ships with the package
        return ImageFont.load_default(size=px)


def intro_card(
    lines: list[str], colour: str, logo: bytes | None, size: tuple[int, int]
) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size, (17, 24, 39))
    d = ImageDraw.Draw(img)
    c = colour.lstrip("#")
    d.rectangle((0, 0, w, h // 9), fill=tuple(int(c[i : i + 2], 16) for i in (0, 2, 4)))
    y = h // 3
    if logo:
        try:
            lg = Image.open(io.BytesIO(logo)).convert("RGBA")
            lg.thumbnail((h // 5, h // 5))
            img.paste(lg, ((w - lg.width) // 2, y - lg.height - 20), lg)
        except OSError:
            pass
    for i, line in enumerate(lines[:5]):
        px = max(18, w // (18 if i == 0 else 26))
        face = font(px, bold=i == 0)
        tw = d.textlength(line, font=face)
        d.text(((w - tw) / 2, y), line, fill=(255, 255, 255), font=face)
        y += int(px * 1.6)
    return img


def draw_overlay(
    frame: Image.Image, ring: tuple[float, float] | None, label: str, show_label: bool
) -> Image.Image:
    d = ImageDraw.Draw(frame)
    w, _ = frame.size
    if ring:
        rx = w * 0.03
        d.ellipse(
            (ring[0] - rx, ring[1] - rx * 0.38, ring[0] + rx, ring[1] + rx * 0.38),
            outline=(250, 204, 21),
            width=4,
        )
    if label and show_label:
        px = max(18, w // 30)
        face = font(px, bold=True)
        tw = d.textlength(label, font=face)
        y = frame.size[1] - px * 3
        d.rectangle((24, y - 8, 24 + tw + 24, y + px + 8), fill=(17, 24, 39))
        d.text((36, y), label, fill=(255, 255, 255), font=face)
    return frame


def render_clip(
    settings: WorkerSettings,
    src: Path,
    clip: dict[str, Any],
    rows: NDArray[np.float32],
    ctx: dict[str, Any],
    out: Path,
) -> None:
    portrait = ctx["format"] == "9x16"
    out_w, out_h = (720, 1280) if portrait else (1280, 720)
    crop_w = round(SRC_H * 9 / 16) if portrait else SRC_W
    a, b = clip["in_ms"], clip["out_ms"]
    n = int((b - a) / 1000 * FPS)
    times = [a + round(i * 1000 / FPS) for i in range(n)]
    where = places(ctx, times)
    lefts = (
        crop_path(rows, times, where, set(ctx["player_tracks"]), crop_w) if portrait else [0] * n
    )
    dec = subprocess.Popen(
        [
            settings.ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-ss",
            f"{a / 1000:.3f}",
            "-t",
            f"{(b - a) / 1000:.3f}",
            "-i",
            str(src),
            "-vf",
            f"scale={SRC_W}:{SRC_H},fps={FPS}",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    enc = subprocess.Popen(
        [
            settings.ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{out_w}x{out_h}",
            "-r",
            str(FPS),
            "-i",
            "-",
            *ENC,
            str(out),
        ],
        stdin=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert dec.stdout is not None and enc.stdin is not None
    # the frame loop blocks on the pipes, so a watchdog stops both processes when they hang
    timed_out = threading.Event()

    def _kill() -> None:
        timed_out.set()
        dec.kill()
        enc.kill()

    watchdog = threading.Timer(FFMPEG_TIMEOUT_S, _kill)
    watchdog.start()
    try:
        # BrokenPipeError: the encoder stopped; its exit code below says why
        with contextlib.suppress(BrokenPipeError):
            try:
                _pipe_frames(
                    dec.stdout, enc.stdin, clip, rows, where, times, lefts, portrait, crop_w
                )
            finally:
                enc.stdin.close()
        dec.wait()
        code = enc.wait()
    finally:
        watchdog.cancel()
        for proc in (dec, enc):
            if proc.poll() is None:  # only after an error in the frame loop
                proc.kill()
                proc.wait()
    if timed_out.is_set():
        raise RuntimeError(f"ffmpeg timed out after {FFMPEG_TIMEOUT_S} s")
    if code != 0:
        raise RuntimeError("encoding failed")


def _pipe_frames(
    stdout: IO[bytes],
    stdin: IO[bytes],
    clip: dict[str, Any],
    rows: NDArray[np.float32],
    where: list[Place | None],
    times: list[int],
    lefts: list[int],
    portrait: bool,
    crop_w: int,
) -> None:
    """Decoded frames in, overlay and crop, encoder frames out."""
    out_w, out_h = (720, 1280) if portrait else (1280, 720)
    a, n = clip["in_ms"], len(times)
    frame_bytes = SRC_W * SRC_H * 3
    i = 0
    while True:
        buf = stdout.read(frame_bytes)
        if len(buf) < frame_bytes:
            break
        img = Image.frombuffer("RGB", (SRC_W, SRC_H), buf, "raw", "RGB", 0, 1)
        t = times[min(i, n - 1)] if n else a
        place = where[min(i, n - 1)] if n else None
        ring = (
            spotlight_at(rows, int(clip["spotlight_track"]), t, place[0], place[1])
            if place is not None and clip.get("spotlight_track") is not None and len(rows)
            else None
        )
        img = draw_overlay(img.copy(), ring, str(clip.get("label") or ""), i < 3 * FPS)
        if portrait:
            left = lefts[min(i, n - 1)] if n else 0
            img = img.crop((left, 0, left + crop_w, SRC_H))
        stdin.write(img.resize((out_w, out_h)).tobytes())
        i += 1


def _rows(
    s3: Any, bucket: str, prefix: str, chunk_ms: int | None, clips: list[dict[str, Any]], work: Path
) -> NDArray[np.float32]:
    if not chunk_ms:
        return np.zeros((0, 4), np.float32)
    needed = sorted(
        {n for c in clips for n in range(c["in_ms"] // chunk_ms, c["out_ms"] // chunk_ms + 1)}
    )
    parts = []
    for n in needed:
        dst = work / f"chunk_{n:05d}.bin"
        try:
            s3.download_file(bucket, f"{prefix}chunk_{n:05d}.bin", str(dst))
            parts.append(np.frombuffer(dst.read_bytes(), dtype="<f4").reshape(-1, 4))
        except Exception as exc:  # missing chunk: no crop or spotlight data for that part
            log.info("chunk_missing", chunk=n, error=str(exc))
    return np.concatenate(parts) if parts else np.zeros((0, 4), np.float32)


def with_views(
    s3: Any, bucket: str, ctx: dict[str, Any], clips: list[dict[str, Any]], work: Path
) -> dict[str, Any]:
    """A moving camera's court refers to the hall image: load the view files (where the camera
    looked, ADR 020) the clips need, as `views`. None of them found: an empty table, so nothing
    is drawn rather than something in the wrong place. A fixed camera: the context as it is."""
    count, chunk_ms = ctx.get("view_chunks"), ctx.get("chunk_ms")
    if not count or not chunk_ms or not ctx.get("frame_size") or ctx.get("homography") is None:
        return ctx
    needed = sorted(
        {
            n
            for c in clips
            for n in range(c["in_ms"] // chunk_ms, c["out_ms"] // chunk_ms + 1)
            if n < int(count)
        }
    )
    parts = []
    for n in needed:
        dst = work / f"view_{n:05d}.bin"
        try:
            s3.download_file(bucket, f"{ctx['chunks_prefix']}view_{n:05d}.bin", str(dst))
            parts.append(np.frombuffer(dst.read_bytes(), dtype="<f4").reshape(-1, VIEW_ROW))
        except Exception as exc:  # missing: no ring or crop for that part
            log.info("view_missing", chunk=n, error=str(exc))
    views = np.concatenate(parts) if parts else np.zeros((0, VIEW_ROW), np.float32)
    return {**ctx, "views": views[np.argsort(views[:, 0], kind="stable")]}


def run_highlight_reel(payload: dict[str, Any]) -> dict[str, Any]:
    return run_artifact_job(
        payload,
        callback_path=f"/internal/highlights/{payload['reel_id']}",
        build=lambda settings, s3, work, _: render_reel(settings, payload, work, s3),
        log=log,
        failed_event="reel_failed",
    )


def render_reel(settings: WorkerSettings, payload: dict[str, Any], work: Path, s3: Any) -> Path:
    """A match in several files (the two halves): `sources` holds each file's proxy, tracks and
    court, and every clip names its `source` with times in that file."""
    if payload.get("sources"):
        return _render_parts(settings, payload, work, s3)
    src = work / "proxy.mp4"
    s3.download_file(payload["bucket_videos"], payload["proxy_key"], str(src))
    logo = _logo(s3, payload)
    rows = _rows(
        s3,
        payload["bucket_artifacts"],
        payload["chunks_prefix"],
        payload.get("chunk_ms"),
        payload["clips"],
        work,
    )
    ctx = with_views(s3, payload["bucket_artifacts"], payload, payload["clips"], work)
    return render_local(settings, ctx, src, rows, logo, work)


def _logo(s3: Any, payload: dict[str, Any]) -> bytes | None:
    if not payload.get("logo_key"):
        return None
    try:
        buf = io.BytesIO()
        s3.download_fileobj(payload["bucket_artifacts"], payload["logo_key"], buf)
        return buf.getvalue()
    except Exception:
        return None


def _render_parts(settings: WorkerSettings, payload: dict[str, Any], work: Path, s3: Any) -> Path:
    files: list[tuple[Path, NDArray[np.float32], dict[str, Any]]] = []
    for i, source in enumerate(payload.get("sources") or []):
        src = work / f"proxy_{i}.mp4"
        s3.download_file(payload["bucket_videos"], source["proxy_key"], str(src))
        mine = [c for c in payload["clips"] if int(c.get("source", 0)) == i]
        sub = work / f"part_{i}"
        sub.mkdir()
        rows = _rows(
            s3,
            payload["bucket_artifacts"],
            source["chunks_prefix"],
            source.get("chunk_ms"),
            mine,
            sub,
        )
        files.append(
            (
                src,
                rows,
                with_views(s3, payload["bucket_artifacts"], {**payload, **source}, mine, sub),
            )
        )
    return render_local(
        settings, payload, files[0][0], files[0][1], _logo(s3, payload), work, files
    )


def render_local(
    settings: WorkerSettings,
    payload: dict[str, Any],
    src: Path,
    rows: NDArray[np.float32],
    logo: bytes | None,
    work: Path,
    files: list[tuple[Path, NDArray[np.float32], dict[str, Any]]] | None = None,
) -> Path:
    """`files`: per source of a match in several files, its proxy, rows and settings (court,
    tracks); each clip's `source` picks one."""
    size = (720, 1280) if payload["format"] == "9x16" else (1280, 720)
    parts: list[Path] = []
    card = work / "intro.png"
    intro_card(payload.get("intro") or [], payload.get("colour", "#0b6bcb"), logo, size).save(card)
    intro = work / "p000.mp4"
    subprocess.run(
        [
            settings.ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-y",
            "-loop",
            "1",
            "-t",
            str(INTRO_S),
            "-i",
            str(card),
            *ENC,
            str(intro),
        ],
        check=True,
        capture_output=True,
        timeout=FFMPEG_TIMEOUT_S,
    )
    parts.append(intro)
    for i, clip in enumerate(payload["clips"], start=1):
        out = work / f"p{i:03d}.mp4"
        if files:
            f_src, f_rows, f_ctx = files[min(int(clip.get("source", 0)), len(files) - 1)]
            render_clip(settings, f_src, clip, f_rows, f_ctx, out)
        else:
            render_clip(settings, src, clip, rows, payload, out)
        parts.append(out)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts))
    final = work / "reel.mp4"
    subprocess.run(
        [
            settings.ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(final),
        ],
        check=True,
        capture_output=True,
        timeout=FFMPEG_TIMEOUT_S,
    )
    return final

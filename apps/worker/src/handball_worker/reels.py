"""Highlight reels (addendum 01, 4.3): intro card, scenes in 16:9 or 9:16, crop that follows the
play, burned-in spotlight and a name strip. Frames are processed in Python between an ffmpeg
decoder and encoder (raw RGB pipes); no music (licences), a hook for a licence-free library can
add an audio track later.
"""

from __future__ import annotations

import contextlib
import io
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import IO, Any

import httpx
import numpy as np
import structlog
from numpy.typing import NDArray
from PIL import Image, ImageDraw, ImageFont

from handball_worker.config import WorkerSettings
from handball_worker.export import ENC, FFMPEG_TIMEOUT_S, FPS

log = structlog.get_logger("worker.reels")
SRC_W, SRC_H = 1280, 720
INTRO_S = 3.0
SMOOTH_FRAMES = 37  # 1.5 s moving average: the crop pans calmly
FrameArray = NDArray[np.uint8]


def project(h: list[list[float]], xy: NDArray[np.float64]) -> NDArray[np.float64]:
    pts = np.c_[xy, np.ones(len(xy))] @ np.asarray(h, dtype=np.float64).T
    out: NDArray[np.float64] = pts[:, :2] / pts[:, 2:3]
    return out


def crop_path(
    rows: NDArray[np.float32],
    times_ms: list[int],
    h: list[list[float]] | None,
    size: tuple[int, int],
    players: set[int],
    crop_w: int,
) -> list[int]:
    """Left edge of a portrait crop per frame: median of the projected players, smoothed."""
    centre = size[0] / 2
    xs: list[float] = []
    for t in times_ms:
        if h is None or len(rows) == 0:
            xs.append(centre)
            continue
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
    rows: NDArray[np.float32], track: int, t: int, h: list[list[float]], size: tuple[int, int]
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
    h, size = ctx.get("homography"), tuple(ctx.get("image_size") or (SRC_W, SRC_H))
    lefts = (
        crop_path(rows, times, h, size, set(ctx["player_tracks"]), crop_w) if portrait else [0] * n
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
                _pipe_frames(dec.stdout, enc.stdin, clip, rows, ctx, times, lefts, portrait, crop_w)
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
    ctx: dict[str, Any],
    times: list[int],
    lefts: list[int],
    portrait: bool,
    crop_w: int,
) -> None:
    """Decoded frames in, overlay and crop, encoder frames out."""
    out_w, out_h = (720, 1280) if portrait else (1280, 720)
    a, n = clip["in_ms"], len(times)
    h, size = ctx.get("homography"), tuple(ctx.get("image_size") or (SRC_W, SRC_H))
    frame_bytes = SRC_W * SRC_H * 3
    i = 0
    while True:
        buf = stdout.read(frame_bytes)
        if len(buf) < frame_bytes:
            break
        img = Image.frombuffer("RGB", (SRC_W, SRC_H), buf, "raw", "RGB", 0, 1)
        t = times[min(i, n - 1)] if n else a
        ring = (
            spotlight_at(rows, int(clip["spotlight_track"]), t, h, size)
            if h and clip.get("spotlight_track") is not None and len(rows)
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


def run_highlight_reel(payload: dict[str, Any]) -> dict[str, Any]:
    settings = WorkerSettings()
    s3 = settings.s3()
    url = f"{settings.api_internal_url.rstrip('/')}/internal/highlights/{payload['reel_id']}"
    headers = {"x-internal-token": settings.internal_token}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            final = render_reel(settings, payload, work, s3)
            s3.upload_file(
                str(final),
                payload["bucket_artifacts"],
                payload["out_key"],
                ExtraArgs={"ContentType": "video/mp4"},
            )
        body: dict[str, Any] = {"status": "ready", "key": payload["out_key"]}
    except Exception as exc:  # reported to the API
        log.warning("reel_failed", error=str(exc))
        body = {"status": "failed", "error": str(exc)[:500]}
    httpx.post(url, json=body, headers=headers, timeout=30).raise_for_status()
    return body


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
    return render_local(settings, payload, src, rows, logo, work)


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
        files.append((src, rows, {**payload, **source}))
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

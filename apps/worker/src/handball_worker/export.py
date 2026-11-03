"""Presentation export as MP4 with burned-in drawings (addendum 01, 4.1).

Every clip slide is cut from the analysis proxy; slow-motion ranges are slowed with setpts, hold
points become still frames with the drawings rendered on top (Pillow), text and stat slides become
short title cards. All pieces are encoded alike (1280x720, 25 fps, no audio) and concatenated.
"""

from __future__ import annotations

import itertools
import math
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import boto3
import httpx
import structlog
from PIL import Image, ImageDraw, ImageFont

from handball_worker.config import WorkerSettings

log = structlog.get_logger("worker.export")
W, H, FPS = 1280, 720, 25
CARD_S = 4.0
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an"]
SCALE = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2"


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)) if len(c) == 6 else (255, 210, 0)


def draw_shapes(img: Image.Image, shapes: list[dict[str, Any]]) -> Image.Image:
    """Same geometry as the web player (normalised points, width relative to 1000 px)."""
    w, h = img.size
    base = img.convert("RGBA")
    over = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    for s in shapes:
        pts = [(x * w, y * h) for x, y in s.get("points", [])]
        if not pts:
            continue
        col = (*_hex(str(s.get("color", "#ffd200"))), 255)
        lw = max(1, round(float(s.get("width", 4)) * w / 1000 + 1))
        a, b = pts[0], pts[-1]
        kind = s.get("kind")
        if kind == "spotlight":
            r = max(math.dist(a, b), 10)
            shade = Image.new("RGBA", base.size, (0, 0, 0, 140))
            ImageDraw.Draw(shade).ellipse(
                (a[0] - r, a[1] - r, a[0] + r, a[1] + r), fill=(0, 0, 0, 0)
            )
            over = Image.alpha_composite(over, shade)
            d = ImageDraw.Draw(over)
            d.ellipse((a[0] - r, a[1] - r, a[0] + r, a[1] + r), outline=col, width=lw)
        elif kind == "circle":
            d.ellipse(
                (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])),
                outline=col,
                width=lw,
            )
        elif kind == "text":
            d.text(
                a,
                str(s.get("text") or ""),
                fill=col,
                font=ImageFont.load_default(size=max(16, lw * 6)),
            )
        else:
            d.line(pts if kind == "freehand" else [a, b], fill=col, width=lw, joint="curve")
            if kind == "arrow" and a != b:
                ang = math.atan2(b[1] - a[1], b[0] - a[0])
                size = lw * 4 + 8
                left = (b[0] - size * math.cos(ang - 0.45), b[1] - size * math.sin(ang - 0.45))
                right = (b[0] - size * math.cos(ang + 0.45), b[1] - size * math.sin(ang + 0.45))
                d.polygon([b, left, right], fill=col)
    return Image.alpha_composite(base, over).convert("RGB")


def card(lines: list[str], path: Path) -> None:
    img = Image.new("RGB", (W, H), (17, 24, 39))
    d = ImageDraw.Draw(img)
    y = H // 2 - 40 * len(lines) // 2
    for i, line in enumerate(lines[:12]):
        font = ImageFont.load_default(size=52 if i == 0 else 34)
        d.text((80, y), line[:80], fill=(255, 255, 255), font=font)
        y += 72 if i == 0 else 50
    img.save(path)


def _ff(settings: WorkerSettings, args: list[str]) -> None:
    subprocess.run(
        [settings.ffmpeg, "-hide_banner", "-nostdin", "-y", *args],
        check=True,
        capture_output=True,
        timeout=900,
    )


def plan_clip(slide: dict[str, Any]) -> list[tuple[str, float, float, float]]:
    """Pieces of a clip slide: ("play", from_s, to_s, rate) and ("hold", t_s, duration_s, 0)."""
    a, b = slide["in_ms"] / 1000, slide["out_ms"] / 1000
    cuts = {a, b}
    slows = [
        (s["from_ms"] / 1000, s["to_ms"] / 1000, float(s.get("rate", 0.5)))
        for s in slide.get("slow", [])
    ]
    holds = sorted(
        (h["t_ms"] / 1000, h.get("duration_ms", 3000) / 1000) for h in slide.get("holds", [])
    )
    for f, t, _ in slows:
        cuts |= {min(max(f, a), b), min(max(t, a), b)}
    for t, _ in holds:
        cuts.add(min(max(t, a), b))
    edges = sorted(cuts)
    pieces: list[tuple[str, float, float, float]] = []
    for x, y in itertools.pairwise(edges):
        for t, dur in holds:
            if abs(t - x) < 1e-3:
                pieces.append(("hold", x, dur, 0.0))
        rate = next((r for f, t, r in slows if f <= x and y <= t), 1.0)
        if y - x > 0.04:
            pieces.append(("play", x, y, rate))
    for t, dur in holds:
        if abs(t - b) < 1e-3:
            pieces.append(("hold", b, dur, 0.0))
    return pieces


def render(
    settings: WorkerSettings, slides: list[dict[str, Any]], sources: dict[str, Path], work: Path
) -> Path:
    parts: list[Path] = []
    for i, slide in enumerate(slides):
        if slide["type"] == "clip" and slide.get("video_id") in sources:
            src = sources[slide["video_id"]]
            for j, (kind, x, y, rate) in enumerate(plan_clip(slide)):
                out = work / f"p{i:03d}_{j:02d}.mp4"
                if kind == "play":
                    _ff(
                        settings,
                        [
                            "-ss",
                            f"{x:.3f}",
                            "-to",
                            f"{y:.3f}",
                            "-i",
                            str(src),
                            "-vf",
                            f"{SCALE},setpts=PTS/{rate}",
                            *ENC,
                            str(out),
                        ],
                    )
                else:
                    still = work / f"s{i:03d}_{j:02d}.png"
                    _ff(
                        settings,
                        [
                            "-ss",
                            f"{x:.3f}",
                            "-i",
                            str(src),
                            "-frames:v",
                            "1",
                            "-vf",
                            SCALE,
                            str(still),
                        ],
                    )
                    shapes: list[dict[str, Any]] = next(
                        (
                            h.get("shapes", [])
                            for h in slide.get("holds", [])
                            if abs(h["t_ms"] / 1000 - x) < 1e-3
                        ),
                        [],
                    )
                    draw_shapes(Image.open(still), shapes).save(still)
                    _ff(
                        settings,
                        [
                            "-loop",
                            "1",
                            "-t",
                            f"{y:.3f}",
                            "-i",
                            str(still),
                            "-vf",
                            SCALE,
                            *ENC,
                            str(out),
                        ],
                    )
                parts.append(out)
        elif slide["type"] in ("text", "stat_card"):
            still = work / f"c{i:03d}.png"
            card(slide.get("lines") or [""], still)
            out = work / f"c{i:03d}.mp4"
            _ff(
                settings,
                ["-loop", "1", "-t", str(CARD_S), "-i", str(still), "-vf", SCALE, *ENC, str(out)],
            )
            parts.append(out)
    if not parts:
        raise ValueError("nothing to export")
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts))
    final = work / "presentation.mp4"
    _ff(
        settings,
        [
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
    )
    return final


def run_presentation_export(payload: dict[str, Any]) -> dict[str, Any]:
    settings = WorkerSettings()
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )
    base = settings.api_internal_url.rstrip("/")
    url = f"{base}/internal/presentations/{payload['presentation_id']}/export"
    headers = {"x-internal-token": settings.internal_token}
    try:
        with tempfile.TemporaryDirectory(
            dir=settings.work_dir if Path(settings.work_dir).exists() else None
        ) as tmp:
            work = Path(tmp)
            sources: dict[str, Path] = {}
            for vid, key in payload["sources"].items():
                dst = work / f"src_{vid}.mp4"
                s3.download_file(payload["bucket_videos"], key, str(dst))
                sources[vid] = dst
            final = render(settings, payload["slides"], sources, work)
            s3.upload_file(
                str(final),
                payload["bucket_artifacts"],
                payload["out_key"],
                ExtraArgs={"ContentType": "video/mp4"},
            )
        body: dict[str, Any] = {"status": "ready", "key": payload["out_key"]}
    except Exception as exc:  # reported to the API, the coach sees the error
        log.warning("presentation_export_failed", error=str(exc))
        body = {"status": "failed", "error": str(exc)[:500]}
    httpx.post(url, json=body, headers=headers, timeout=30).raise_for_status()
    return body

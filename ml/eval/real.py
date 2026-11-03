"""Real-video evaluation (Q-DATA-1): run the analysis on the real test videos in data/videos/.

Real clips have no ground truth yet (Q-DATA-3), so this measures health, not accuracy:

1. Camera: fixed or moving (`camera_moves`); for moving cameras the camera motion (pan range, zoom,
   share of frames placed on the panorama, focal length) and the hall panorama.
2. Calibration: automatic, on the median frame (fixed) or on the panorama (moving), or from clicked
   points stored in the manifest (`calibration`: frame index plus image/court point pairs).
3. If calibrated: the full analysis on the first --seconds, with detections per frame, track
   fragmentation (raw vs. stitched tracks), team split and speed.

Videos come from ml/eval/golden_set/manifest.json and are expected under data/videos/ (`make testdata`).
Entries without a local file are listed as missing. Debug images (panoramas, line masks) go to
data/eval-real/.

    uv run python ml/eval/real.py [--seconds 30] [--out docs/perf/eval-real.md] [ID ...]
"""

from __future__ import annotations

import argparse
import itertools
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from handball_vision.calibration import (
    Calibration,
    CalibrationError,
    calibrate_frames,
    calibrate_points,
    line_masks,
)
from handball_vision.motion import CameraMotion, estimate_motion
from handball_vision.pipeline import _open, analyse_video, camera_moves, iter_frames, sample_frames

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "ml" / "eval" / "golden_set" / "manifest.json"
VIDEO_DIR = ROOT / "data" / "videos"
DEBUG_DIR = ROOT / "data" / "eval-real"


def hex_to_bgr(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    r, g, b = (int(v[i : i + 2], 16) for i in (0, 2, 4))
    return (b, g, r)


def write_debug(entry_id: str, image: Any) -> None:
    """Image (frame or panorama) with the white / dark / red line masks overlaid."""
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    masks = line_masks(image)
    overlay = image.copy()
    for name, colour in (("white", (0, 0, 255)), ("dark", (255, 0, 0)), ("red", (0, 255, 0))):
        overlay[masks[name] > 0] = colour
    out = np.vstack([image, overlay])
    width = min(1600, out.shape[1])
    out = cv2.resize(out, (width, round(out.shape[0] * width / out.shape[1])))
    cv2.imwrite(str(DEBUG_DIR / f"{entry_id}-lines.jpg"), out)


def write_court(
    entry_id: str, image: Any, calib: Calibration, motion: CameraMotion | None, path: Path
) -> None:
    """Court lines drawn on the panorama (or median frame) and on four frames across the clip."""
    from handball_court import COURT
    from handball_vision import geometry
    from handball_vision.detection import _clip_front

    def draw(img: Any, h: Any) -> Any:
        out = img.copy()
        for line in COURT.lines.values():
            pts = np.array(line, np.float64)
            for a, b in itertools.pairwise(pts):
                seg = _clip_front(h, np.array([a, b, b, a]))
                if len(seg) >= 2:
                    p = np.clip(geometry.apply(h, seg[:2]), -1e4, 1e4).round().astype(np.int32)
                    cv2.line(out, tuple(p[0]), tuple(p[1]), (0, 0, 255), 2, cv2.LINE_AA)
        return out

    tiles = [draw(image, calib.homography)]
    container, _, _, total = _open(path)
    container.close()
    wanted = {round(total * k / 5) for k in (1, 2, 3, 4)}
    for i, frame in enumerate(iter_frames(path)):
        if i in wanted:
            h_frame = motion.canvas_to_frame(i) if motion is not None else np.eye(3)
            if h_frame is not None:
                tiles.append(draw(frame, h_frame @ calib.homography))
        if i > max(wanted):
            break
    width = 1600
    rows = [
        cv2.resize(tile, (width, round(tile.shape[0] * width / tile.shape[1]))) for tile in tiles
    ]
    cv2.imwrite(str(DEBUG_DIR / f"{entry_id}-court.jpg"), np.vstack(rows))


def manual_calibration(
    entry: dict[str, Any], size: tuple[int, int]
) -> tuple[Calibration, int] | None:
    spec = entry.get("calibration")
    if not spec:
        return None
    pts = spec["points"]
    calib = calibrate_points(
        [tuple(p["image"]) for p in pts], [tuple(p["court"]) for p in pts], size
    )
    return calib, int(spec.get("frame", 0))


def evaluate(entry: dict[str, Any], path: Path, seconds: float) -> dict[str, Any]:
    row: dict[str, Any] = {"id": entry["id"]}
    container, _, fps, total = _open(path)
    container.close()
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    moving = camera_moves(path)
    motion: CameraMotion | None = None
    if moving:
        motion = estimate_motion(iter_frames(path), expected_frames=total)
        image = motion.background()
        s = motion.stats
        row["camera"] = (
            f"moving: pan {s.get('pan_deg', 0):.0f}°, zoom x{s.get('zoom_ratio', 1):.2f},"
            f" {motion.coverage:.0%} of frames placed, f {s.get('focal_px', 0):.0f} px"
        )
        row["motion_s"] = round(time.perf_counter() - t0, 1)
        cv2.imwrite(str(DEBUG_DIR / f"{entry['id']}-pano.jpg"), image)
    else:
        image = np.median(np.stack(sample_frames(path, 24)), axis=0).astype(np.uint8)
        row["camera"] = "fixed"
    write_debug(entry["id"], image)

    manual = manual_calibration(
        entry, (image.shape[1], image.shape[0]) if not moving else _frame_size(path)
    )
    calib: Calibration | None = None
    calib_frame = 0
    if manual is not None:
        calib, calib_frame = manual
        row["calibration"] = f"manual ({calib.reprojection_px:.1f} px)"
    else:
        try:
            calib = calibrate_frames(
                [image],
                seen=motion.seen() if motion else None,
                intrinsics=motion.canvas_intrinsics() if motion and motion.moving else None,
            )
            row["calibration"] = f"ok (conf {calib.confidence:.2f})"
        except CalibrationError as e:
            row["calibration"] = f"failed: {e}"

    if calib is None:
        row["analysis"] = "skipped (no calibration)"
        return row
    if manual is None:
        write_court(entry["id"], image, calib, motion, path)
    kits = {k: hex_to_bgr(v) for k, v in (entry.get("kits") or {}).items()}
    if len(kits) != 2:
        row["analysis"] = "skipped (no kits in manifest)"
        return row
    t0 = time.perf_counter()
    res = analyse_video(
        path,
        kits,
        calibration=calib if manual is not None else None,
        calibration_frame=calib_frame,
        max_frames=int(seconds * fps),
        motion=motion if motion is not None else False,
    )
    wall = time.perf_counter() - t0
    labels = Counter(str(t["label"]) for t in res.teams.values())
    row["analysis"] = "ok"
    row["detections_per_frame"] = round(res.detections_per_frame, 1)
    row["raw_tracks"] = res.extra["raw_tracks"]
    row["tracks"] = res.extra["tracks"]
    row["team_split"] = dict(labels)
    row["realtime_factor"] = round(wall / max(1e-9, res.frames / res.fps), 2)
    return row


def _frame_size(path: Path) -> tuple[int, int]:
    container, stream, _, _ = _open(path)
    try:
        return (stream.codec_context.width, stream.codec_context.height)
    finally:
        container.close()


def to_markdown(rows: list[dict[str, Any]], seconds: float) -> str:
    lines = [
        "# Real-video evaluation",
        "",
        f"Generated by `ml/eval/real.py` (analysis on the first {seconds:.0f} s when calibrated)."
        " No ground truth yet (Q-DATA-3): these are health checks, not accuracy. Panoramas and line"
        " masks: `data/eval-real/` (local only)."
        " Calibration `ok` is the pipeline's own check; on real halls it is not reliable yet, verify"
        " with `data/eval-real/*-court.jpg` (court lines on the panorama and on four frames).",
        "",
        "| Clip | Camera | Calibration | Analysis |",
        "|---|---|---|---|",
    ]
    for r in rows:
        if r.get("missing"):
            lines.append(f"| {r['id']} | missing locally | | |")
            continue
        analysis = r["analysis"]
        if analysis == "ok":
            analysis = (
                f"{r['detections_per_frame']} det/frame, {r['raw_tracks']}->{r['tracks']} tracks,"
                f" teams {r['team_split']}, {r['realtime_factor']}x realtime"
            )
        lines.append(f"| {r['id']} | {r['camera']} | {r['calibration']} | {analysis} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--seconds", type=float, default=30.0)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))["matches"]
    if args.ids:
        entries = [e for e in entries if e["id"] in args.ids]
    if not entries:
        print("no entries in the manifest (see data/README.md)")
        return 1
    rows = []
    for entry in entries:
        path = VIDEO_DIR / Path(entry["key"]).name
        if not path.exists():
            rows.append({"id": entry["id"], "missing": True})
            print(f"missing     {entry['id']} (run make testdata)")
            continue
        print(f"evaluate    {entry['id']}", flush=True)
        rows.append(evaluate(entry, path, args.seconds))
        print(f"            {rows[-1]}", flush=True)
    md = to_markdown(rows, args.seconds)
    print(md)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

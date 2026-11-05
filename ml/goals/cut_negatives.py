"""Non-goal clips from the same game: 9-second windows at least `--gap` seconds away from every
officially logged event, cut from the 3-minute segments with the same ffmpeg settings as the goal
clips (`ml/eval/cut_event_clips.py`: 1280 wide, libx264 veryfast crf 21), so resolution and
compression are no give-away.

The segment start in the full video comes from `--starts` (seconds, one per segment; found by
reading the overlay clock, see README). Windows tile each segment with a stride of `--stride` s.

usage: python ml/goals/cut_negatives.py ALIGNED.json OUT_DIR --segs s0.mp4,s1.mp4,...
       --starts 855.1,1710.2,... [--gap 20] [--stride 9] [--len 9]
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("aligned", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--segs", required=True)
    ap.add_argument("--starts", required=True)
    ap.add_argument("--seg-len", type=float, default=180.0)
    ap.add_argument("--gap", type=float, default=20.0)
    ap.add_argument("--stride", type=float, default=9.0)
    ap.add_argument("--len", type=float, default=9.0)
    a = ap.parse_args()
    events = [e["video_ms"] / 1000 for e in json.loads(a.aligned.read_text())["entries"]
              if e.get("video_ms") is not None]
    a.out.mkdir(parents=True, exist_ok=True)
    index = []
    for seg, start in zip(a.segs.split(","), (float(s) for s in a.starts.split(",")), strict=True):
        t = 0.0
        while t + a.len <= a.seg_len - 0.5:
            v0, v1 = start + t, start + t + a.len
            near = min((max(v0 - e, e - v1, 0.0) for e in events), default=1e9)
            if near >= a.gap:
                name = f"neg_{Path(seg).stem.split('_')[-1]}_{round(v0)}s.mp4"
                subprocess.run(  # noqa: S603
                    ["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-t", f"{a.len:.2f}",  # noqa: S607
                     "-i", seg, "-an", "-vf", "scale='min(1280,iw)':-2", "-c:v", "libx264",
                     "-preset", "veryfast", "-crf", "21", str(a.out / name)],
                    check=True,
                )
                index.append({"clip": name, "segment": seg, "seg_start_s": t,
                              "video_ms": round(v0 * 1000), "nearest_event_s": round(near, 1)})
            t += a.stride
    (a.out / "index.json").write_text(json.dumps(index, indent=1))
    print(len(index), "negative clips in", a.out)


if __name__ == "__main__":
    main()

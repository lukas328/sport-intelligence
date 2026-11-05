"""Short clips around officially logged events (goals, shots, saves) from an aligned log
(`align_official.py`): the raw material for goal and shot scenes without hand labelling.

The logged time is when the table entered the event, typically 4 to 6 s after the goal (ml/goals),
so each clip spans `before` seconds before to `after` seconds after it.

usage: python ml/eval/cut_event_clips.py VIDEO ALIGNED.json OUT_DIR [--kinds goal,penalty_goal]
       [--before 12] [--after 3] [--width 1280]
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def wanted(entry: dict[str, Any], kinds: set[str]) -> bool:
    return entry.get("video_ms") is not None and str(entry.get("kind")) in kinds


def clip_name(entry: dict[str, Any], k: int) -> str:
    t = round(int(entry["video_ms"]) / 1000)
    who = entry.get("number")
    return f"{k:03d}_{entry.get('kind')}_{entry.get('team') or 'x'}_{who if who is not None else 'x'}_{t}s.mp4"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("aligned", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--kinds", default="goal,penalty_goal")
    ap.add_argument("--before", type=float, default=12.0)
    ap.add_argument("--after", type=float, default=3.0)
    ap.add_argument("--width", type=int, default=1280)
    a = ap.parse_args()
    kinds = set(a.kinds.split(","))
    data = json.loads(a.aligned.read_text())
    a.out.mkdir(parents=True, exist_ok=True)
    index = []
    for k, e in enumerate(x for x in data.get("entries", []) if wanted(x, kinds)):
        start = max(0.0, int(e["video_ms"]) / 1000 - a.before)
        name = clip_name(e, k)
        subprocess.run(
            [  # noqa: S607
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-ss",
                f"{start:.2f}",
                "-t",
                f"{a.before + a.after:.2f}",
                "-i",
                str(a.video),
                "-an",
                "-vf",
                f"scale='min({a.width},iw)':-2",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "21",
                str(a.out / name),
            ],
            check=True,
        )
        index.append({**e, "clip": name, "clip_start_ms": round(start * 1000)})
    (a.out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))
    print(len(index), "clips in", a.out)


if __name__ == "__main__":
    main()

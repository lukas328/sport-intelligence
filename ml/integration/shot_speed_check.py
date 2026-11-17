"""Is the shot the fastest ball of its clip? A first check of shot events from the ball path
(docs/plans/produkt-analyse-integration.md step 5) on the 41 dev shot clips of
ml/gold/shot_clips.json. The "test" split is dropped before anything else and never read.

Ball path: the product tracker (`handball_vision.balltrack2`, no OWLv2) on the hr1 + hrp1
candidates of Modal job 12 (Kaggle dataset handball-gpu-prelabel-shots); optionally in canvas
pixels (camera motion of the clip from `handball_vision.motion.MotionEstimator`, CANVAS_JSON).
Speed: px per frame at 30 fps (1280 px wide), steps within the tracker's limit (70) only,
"sustained" = the lowest speed over n consecutive steps. Check: the clip's fastest sustained ball
lies in [log - 3 s, log + 1 s] (log = the official log time of the shot), which covers 4 of the
clip's 9 to 10 s, so chance is about 0.4.

    uv run python ml/integration/shot_speed_check.py PRE_HR1 PRE_HRP1 [CANVAS_JSON]
"""

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLD = HERE.parent / "gold"
sys.path.insert(0, str(GOLD))
from tracker_eval_conf import ensemble, no_owl  # noqa: E402

from handball_vision import balltrack2  # noqa: E402


def speeds(pts, conf, fps, cmin):
    sc = 30 / fps
    sp = [None]
    for k in range(1, len(pts)):
        a, b = pts[k - 1], pts[k]
        ok = a and b and conf[k] >= cmin and conf[k - 1] >= cmin
        v = math.hypot(b[0] - a[0], b[1] - a[1]) / sc if ok else None
        sp.append(v if v is not None and v <= 70 else None)
    return sp


def sustained(sp, n):
    out = [0.0] * len(sp)
    for k in range(len(sp) - n + 1):
        w = sp[k : k + n]
        if all(s is not None for s in w):
            out[k] = min(w)
    return out


def main():
    meta = {c["id"]: c for c in json.loads((GOLD / "shot_clips.json").read_text())["clips"]}
    dev = [cid for cid, c in meta.items() if c["split"] == "dev"]
    pa = json.loads(Path(sys.argv[1]).read_text())["clips"]
    pb = json.loads(Path(sys.argv[2]).read_text())["clips"]
    pa = {cid: pa[cid] for cid in dev}
    pb = {cid: pb[cid] for cid in dev}
    canvas = json.loads(Path(sys.argv[3]).read_text()) if len(sys.argv) > 3 else {}
    ens = no_owl(ensemble(pa, pb))
    paths = {}
    for cid in dev:
        c = ens[cid]
        fps = c.get("fps_read", c["fps"])
        out, conf = balltrack2.track([[tuple(v) for v in r["net"]] for r in c["pre"]], fps, c["w"])
        paths[cid] = (fps, out, conf)
    for space in ("frame", "canvas") if canvas else ("frame",):
        for cmin in (0.0, 0.3):
            for n in (1, 4, 8):
                hits = 0
                for cid, (fps, out, conf) in paths.items():
                    pts = out if space == "frame" else canvas[cid]
                    f1, log = round(fps), round(meta[cid]["shot"]["log_ms"] / 1000 * fps)
                    s = sustained(speeds(pts, conf, fps, cmin), max(1, round(n * fps / 30)))
                    near = max(s[max(0, log - 3 * f1) : log + f1] or [0])
                    far = max(s[: max(0, log - 3 * f1)] + s[log + f1 :] or [0])
                    hits += near > far
                print(
                    f"{space:6} conf >= {cmin} sustained {n}: fastest near the log time {hits}/{len(paths)}"
                )


if __name__ == "__main__":
    main()

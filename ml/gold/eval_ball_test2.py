"""Ball nets on ball test 2 (gold v2, frozen LLM labels, ml/gold/data/ball_test2_labels.json).

Per labelled frame the net sees the three frames t-G, t, t+G (G = 3 above 40 fps, else 2) at 1280 px
wide, as in the prelabel kernel (ml/gold/kaggle/prelabel_gpu.py), and gives its top peak.
Measures: on the 85 ball frames top-1 within 12 px (and 25 px) of the label; at score thresholds
0.3 / 0.5: balls found (top-1 within 12 px and above the threshold) and frames without a ball with a
peak above it (false alarms, 30 frames); 95 % intervals from a bootstrap over games; paired
gained / lost between the nets. Only for comparing nets measured once each; never tune on it.

    python ml/gold/eval_ball_test2.py VIDEOS_DIR NAME=ARCH:WEIGHTS [NAME=ARCH:WEIGHTS ...] [--out R.json]
        [--labels ml/gold/data/ball_val1_labels.json]  # the validation set: all decisions there
ARCH: ballhr or ballhrp (ml/ball/ballhr.py, ml/ball/ballhrp.py). Needs torch (CPU is enough).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml/ball"))
LABELS = ROOT / "ml/gold/data/ball_test2_labels.json"
R_HIT, R_NEAR = 12.0, 25.0


def load_net(arch: str, weights: str) -> torch.nn.Module:
    if arch == "ballhr":
        from ballhr import BallHR

        net: torch.nn.Module = BallHR()
    else:
        from ballhrp import BallHRP

        net = BallHRP(pretrained=False)
    net.load_state_dict(torch.load(weights, map_location="cpu", weights_only=True))
    return net.eval()


def triplet(video: Path, frame: int, fps: float) -> np.ndarray:
    g = 3 if fps > 40 else 2
    cap = cv2.VideoCapture(str(video))
    ims = []
    for f in (frame - g, frame, frame + g):
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, f))
        ok, im = cap.read()
        if not ok:
            raise RuntimeError(f"{video} frame {f}")
        if im.shape[1] != 1280:
            im = cv2.resize(
                im, (1280, round(im.shape[0] * 1280 / im.shape[1])), interpolation=cv2.INTER_AREA
            )
        ims.append(im)
    cap.release()
    h2 = ims[0].shape[0] // 32 * 32
    rgb = [cv2.cvtColor(im[:h2], cv2.COLOR_BGR2RGB) for im in ims]
    return np.concatenate(rgb, 2).transpose(2, 0, 1)[None].astype(np.float32)


def top_peak(net: torch.nn.Module, x: np.ndarray) -> tuple[float, float, float]:
    with torch.no_grad():
        hm = torch.sigmoid(net(torch.from_numpy(x)))[0, 0].numpy()
    y, xx = np.unravel_index(hm.argmax(), hm.shape)
    return float(xx * 4 + 2), float(y * 4 + 2), float(hm[y, xx])


def boot(vals: list[float], games: list[str], n: int = 2000) -> list[float]:
    gs = sorted(set(games))
    idx = {g: [i for i, h in enumerate(games) if h == g] for g in gs}
    rng = np.random.default_rng(0)
    out = []
    for _ in range(n):
        pick = [i for g in rng.choice(gs, len(gs)) for i in idx[g]]
        out.append(float(np.mean([vals[i] for i in pick])) if pick else float("nan"))
    return [round(float(v), 3) for v in np.nanpercentile(out, [2.5, 97.5])]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", type=Path)
    ap.add_argument("nets", nargs="+")
    ap.add_argument("--out", type=Path)
    ap.add_argument(
        "--labels",
        type=Path,
        default=LABELS,
        help="another frozen label file (e.g. the validation set)",
    )
    a = ap.parse_args()
    torch.set_num_threads(4)
    labels = [
        r for r in json.loads(a.labels.read_text())["labels"] if r["label"] in ("ball", "no_ball")
    ]
    nets = {}
    for spec in a.nets:
        name, rest = spec.split("=", 1)
        arch, weights = rest.split(":", 1)
        nets[name] = load_net(arch, weights)
    preds: dict[str, list[tuple[float, float, float]]] = {k: [] for k in nets}
    for i, r in enumerate(labels):
        x = triplet(a.videos / r["file"], r["frame"], r["fps"])
        for k, net in nets.items():
            preds[k].append(top_peak(net, x))
        print(
            i,
            r["id"],
            r["label"],
            {k: [round(v, 2) for v in p[-1]] for k, p in preds.items()},
            flush=True,
        )
    balls = [i for i, r in enumerate(labels) if r["label"] == "ball"]
    empty = [i for i, r in enumerate(labels) if r["label"] == "no_ball"]
    games_b = [labels[i]["game"] for i in balls]
    games_e = [labels[i]["game"] for i in empty]
    res: dict[str, dict] = {"balls": len(balls), "no_ball_frames": len(empty)}
    hits: dict[str, list[float]] = {}
    for k, p in preds.items():
        d = [math.hypot(p[i][0] - labels[i]["x"], p[i][1] - labels[i]["y"]) for i in balls]
        hit = [float(v <= R_HIT) for v in d]
        hits[k] = hit
        row: dict = {
            "top1_12px": round(float(np.mean(hit)), 3),
            "top1_12px_ci": boot(hit, games_b),
            "top1_25px": round(float(np.mean([v <= R_NEAR for v in d])), 3),
        }
        for th in (0.3, 0.5):
            found = [float(d[j] <= R_HIT and p[i][2] >= th) for j, i in enumerate(balls)]
            fa = [float(p[i][2] >= th) for i in empty]
            row[f"at_{th}"] = {
                "found": round(float(np.mean(found)), 3),
                "found_ci": boot(found, games_b),
                "false_alarm_frames": round(float(np.mean(fa)), 3),
                "false_alarm_ci": boot(fa, games_e),
            }
        res[k] = row
    names = list(preds)
    for x_ in range(len(names)):
        for y_ in range(x_ + 1, len(names)):
            a_, b_ = hits[names[x_]], hits[names[y_]]
            res[f"{names[x_]} vs {names[y_]}"] = {
                "only_first": int(sum(u and not v for u, v in zip(a_, b_, strict=True))),
                "only_second": int(sum(v and not u for u, v in zip(a_, b_, strict=True))),
            }
    out = json.dumps(res, indent=1)
    print(out)
    if a.out:
        a.out.write_text(out)


if __name__ == "__main__":
    main()

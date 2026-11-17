"""Shot gold, step 1: tracker v2 points on the dev shot clips as "Ball hier?" items for the owner.

Input: two merged prelabel outputs of Modal job 12 (`ml/gpu/prelabel_clips.py`, dataset
handball-gpu-prelabel-shots: hrp1 with OWLv2 every 4th frame, hr1 without), the clip mp4s of the
dev split of `shot_clips.json`. The "test" split is never read (frozen final test).

The tracker runs exactly as on gold v1 (hr1 + hrp1 net candidates merged within 8 px with the mean
score, OWLv2 from hrp1, rescoring with OWLv2 weights, confidence per point). Frames are sampled per
clip, denser around the logged shot time (the shot clip's `log_ms`, 7 s into the clip):
every 0.5 s from 4 s before to 1 s after it, and three frames outside that window. Each item shows the
tracker's point (or, where the tracker has none, the best merged candidate) as a ring on three
frames f-1, f, f+1 (96 px crops, 2x) and the whole frame below (960 px wide, clickable).

    python ml/gold/shot_check.py PRE_HR1 PRE_HRP1 CLIPS_DIR OUT_DIR
writes OUT_DIR/s/<sheet>.jpg (10 items per sheet), OUT_DIR/items.json and OUT_DIR/tracks.json
(full tracker path and confidence per dev clip, for later scoring against the owner's answers).
"""

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tracker import Params, track_clip_conf  # noqa: E402
from tracker_eval_conf import ensemble  # noqa: E402

R, CH, XW = 48, 192, 960
WINDOW = (-4.0, 1.0, 0.5)  # s around the logged time: from, to, step
OUTSIDE = (0.5, 2.0, 9.25)  # s into the clip


def sample_times(log_s: float, dur_s: float) -> list[float]:
    a, b, step = WINDOW
    ts = [log_s + a + i * step for i in range(round((b - a) / step) + 1)]
    ts += [t for t in OUTSIDE if not (log_s + a <= t <= log_s + b)]
    return sorted(t for t in ts if 0 <= t < dur_s)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pre_hr1", type=Path)
    ap.add_argument("pre_hrp1", type=Path)
    ap.add_argument("clips_dir", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    meta = {c["id"]: c for c in json.loads((HERE / "shot_clips.json").read_text())["clips"]}
    dev = [cid for cid, c in meta.items() if c["split"] == "dev"]
    pa = json.loads(a.pre_hr1.read_text())["clips"]
    pb = json.loads(a.pre_hrp1.read_text())["clips"]
    pa = {cid: pa[cid] for cid in dev}  # the test split is dropped before anything else
    pb = {cid: pb[cid] for cid in dev}
    ens = ensemble(pa, pb)
    (a.out / "s").mkdir(parents=True, exist_ok=True)
    items, tracks, sheet, sid = [], {}, [], 0

    def flush() -> None:
        nonlocal sheet, sid
        if sheet:
            cv2.imwrite(
                str(a.out / "s" / f"{sid:03d}.jpg"),
                np.vstack(sheet),
                [cv2.IMWRITE_JPEG_QUALITY, 80],
            )
            sheet, sid = [], sid + 1

    cover = []
    for cid in dev:
        c = ens[cid]
        tr, conf = track_clip_conf(c, Params())
        tracks[cid] = {"track": tr, "conf": [round(v, 3) for v in conf]}
        cover.append(sum(q is not None for q in tr) / len(tr))
        cap = cv2.VideoCapture(str(a.clips_dir / f"{cid}.mp4"))
        fr = []
        while True:
            ok, im = cap.read()
            if not ok:
                break
            fr.append(im)
        if len(fr) != len(tr):
            print(f"{cid}: {len(fr)} video frames, {len(tr)} prelabel frames", file=sys.stderr)
        fps = c.get("fps_read", c["fps"])
        h, w = fr[0].shape[:2]
        xh = round(h * XW / w)
        log_s = meta[cid]["shot"]["log_ms"] / 1000
        for t in sample_times(log_s, len(fr) / fps):
            f = min(len(fr) - 1, round(t * fps))
            q = tr[f]
            if q is not None:
                x, y, src = q[0], q[1], "tracker"
            else:
                cands = [(s, cx, cy) for cx, cy, s in c["pre"][f]["net"]]
                cands += [(o[4], o[0], o[1]) for o in c["pre"][f].get("owl", [])]
                _s, x, y = max(cands) if cands else (0, w / 2, h / 2)
                src = "cand"
            crops = []
            for j in (max(0, f - 1), f, min(len(fr) - 1, f + 1)):
                pad = cv2.copyMakeBorder(fr[j], R, R, R, R, cv2.BORDER_CONSTANT)
                cr = pad[round(y) : round(y) + 2 * R, round(x) : round(x) + 2 * R]
                crops.append(cv2.resize(cr, (CH, CH), interpolation=cv2.INTER_NEAREST))
            top = np.zeros((CH, XW, 3), np.uint8)
            top[:, : 3 * CH] = np.hstack(crops)
            sheet.append(
                np.vstack([top, cv2.resize(fr[f], (XW, xh), interpolation=cv2.INTER_AREA)])
            )
            items.append(
                {
                    "id": f"{cid}_{f}",
                    "k": f"{len(items):03d}",
                    "ch": CH,
                    "cw": 3 * CH,
                    "xh": xh,
                    "xw": XW,
                    "game": meta[cid]["game"],
                    "video": cid,
                    "frame": f,
                    "t": round(t - log_s, 2),
                    "x": round(x * 1280 / w, 1),
                    "y": round(y * 1280 / w, 1),
                    "fw": w,
                    "from": src,
                    "conf": round(conf[f], 3) if q is not None else 0.0,
                    "kind": meta[cid]["shot"]["kind"],
                    "sheet": f"s/{sid:03d}.jpg",
                    "sy": (len(sheet) - 1) * (CH + xh),
                }
            )
            if len(sheet) == 10:
                flush()
        flush()  # sheets never mix clips of different height
    (a.out / "items.json").write_text(json.dumps(items))
    (a.out / "tracks.json").write_text(json.dumps(tracks))
    n_tr = sum(i["from"] == "tracker" for i in items)
    print(
        f"{len(dev)} dev clips, tracker point on {sum(cover) / len(cover):.1%} of frames (mean per clip);"
        f" {len(items)} items ({n_tr} tracker, {len(items) - n_tr} candidate), {sid} sheets"
    )
    print(
        "low coverage:", [(cid, round(v, 2)) for cid, v in zip(dev, cover, strict=False) if v < 0.5]
    )


if __name__ == "__main__":
    main()

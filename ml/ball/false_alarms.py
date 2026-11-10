"""What do the false peaks of the 3-frame ball nets sit on? (test set 2, CPU only)

Three stages, because the net needs torch and the pose model needs rtmlib/onnxruntime (two venvs):

    # 1. peaks of each net (torch venv): top 5 per frame, local motion of each peak over the triplet
    python ml/ball/false_alarms.py peaks ITEMS_JSON LABELS_DIR T_DIR PEAKS.json MODEL.pt [MODEL.pt ...]
    # 2. people and keypoints on the centre frame (venv with rtmlib + onnxruntime, Apache-2.0)
    python ml/ball/false_alarms.py pose ITEMS_JSON LABELS_DIR T_DIR POSE.json
    # 3. categories, numbers and a contact sheet (any venv with opencv + numpy)
    python ml/ball/false_alarms.py report ITEMS_JSON LABELS_DIR T_DIR PEAKS.json POSE.json SHEET.jpg

False peak: on a frame without a ball every peak >= 0.4 of the top 5; on a ball frame every such peak
more than 12 px (1280-wide frame) from the labelled ball. Categories by the nearest COCO keypoint of
an RTMPose person (score >= 0.3) within max(10 px, 0.1 x person height): head (nose, eyes, ears),
hand (wrists), foot (ankles); else "body" inside a person box (5 % margin), else "off-body".
"Static": local motion against its own surroundings < 0.2 (as MOVE_LOCAL in kaggle/train_r6.py;
real balls >= 0.2, fixed spots below). Deterministic: no sampling, fixed thresholds.
"""
import collections, glob, json, math, sys
from pathlib import Path

import cv2, numpy as np

R_HIT, P_MIN, MOVE_LOCAL, KP_MIN = 12, 0.4, 0.2, 0.3
GROUPS = {"head": (0, 1, 2, 3, 4), "hand": (9, 10), "foot": (15, 16)}
CATS = ("head", "hand", "foot", "body", "off-body")


def load(items_json, labels_dir):
    items = {i["id"]: i for i in json.load(open(items_json))}
    labels = {}
    for f in sorted(glob.glob(str(Path(labels_dir) / "*.json"))):
        d = json.load(open(f)); labels[Path(f).stem] = d.get("data", d)
    labels = {k: v for k, v in sorted(labels.items()) if v["state"] in ("ball", "none") and k in items}
    return items, labels


def triplet(items, tdir, k):
    it = items[k]; t = cv2.imread(str(Path(tdir) / f"{it.get('k', k)}.jpg")); W = it["w"]
    return [t[:, j * W:(j + 1) * W] for j in range(3)]  # BGR, centre frame = [1]


def local_motion(trip, cx, cy, r=64, q=8):
    """How much the spot moves against its own surroundings (0: glued to the background); mine_gpu.py."""
    H, W = trip[0].shape[:2]; x0 = int(np.clip(cx - r, 0, W - 2 * r)); y0 = int(np.clip(cy - r, 0, H - 2 * r))
    g = [cv2.cvtColor(t[y0:y0 + 2 * r, x0:x0 + 2 * r], cv2.COLOR_BGR2GRAY).astype(np.float32) for t in trip]
    px, py = int(cx - x0), int(cy - y0); c = g[1][max(0, py - q):py + q, max(0, px - q):px + q]
    if c.size == 0:
        return 0.0
    contrast = float(c.std()) + 4.0; out = []
    for o in (g[0], g[2]):
        (dx, dy), _ = cv2.phaseCorrelate(g[1], o)
        M = np.float32([[1, 0, -dx], [0, 1, -dy]]); al = cv2.warpAffine(o, M, (2 * r, 2 * r), borderMode=cv2.BORDER_REPLICATE)
        a = al[max(0, py - q):py + q, max(0, px - q):px + q]; out.append(float(np.abs(a - c).mean()) / contrast)
    return min(out)


def stage_peaks(items_json, labels_dir, tdir, out, *models):
    import torch
    sys.path.insert(0, str(Path(__file__).parent))
    from bench_testset2 import BallNet3, peaks
    torch.manual_seed(0); torch.set_num_threads(4); torch.use_deterministic_algorithms(True)
    items, labels = load(items_json, labels_dir); res = {}
    for mp in models:
        net = BallNet3(); net.load_state_dict(torch.load(mp, map_location="cpu", weights_only=True)); net.eval()
        rows = {}
        for k in labels:
            trip = triplet(items, tdir, k); ims = [cv2.cvtColor(i, cv2.COLOR_BGR2RGB) for i in trip]
            h2, w2 = ims[0].shape[0] // 32 * 32, ims[0].shape[1] // 32 * 32
            x = torch.from_numpy(np.concatenate([i[:h2, :w2] for i in ims], 2).transpose(2, 0, 1)[None].astype(np.float32))
            with torch.no_grad():
                hm = torch.sigmoid(net(x))[0, 0].numpy()
            rows[k] = [[int(px), int(py), round(s, 4), round(local_motion(trip, px, py), 4)] for px, py, s in peaks(hm)]
        res[Path(mp).stem] = rows; print(Path(mp).stem, len(rows), "frames", flush=True)
    ball_motion = {k: round(local_motion(triplet(items, tdir, k), l["x"], l["y"]), 4)
                   for k, l in labels.items() if l["state"] == "ball"}
    json.dump({"peaks": res, "ball_motion": ball_motion}, open(out, "w"))


def stage_pose(items_json, labels_dir, tdir, out):
    from rtmlib import Body  # RTMPose + YOLOX person detector, ONNX on CPU
    body = Body(mode="balanced", backend="onnxruntime", device="cpu")
    items, labels = load(items_json, labels_dir); res = {}
    for n, k in enumerate(labels):
        img = triplet(items, tdir, k)[1]
        boxes = body.det_model(img)
        kps, scores = body.pose_model(img, bboxes=boxes) if len(boxes) else (np.zeros((0, 17, 2)), np.zeros((0, 17)))
        res[k] = [{"box": [round(float(v), 1) for v in b[:4]], "kp": np.round(p, 1).tolist(), "s": np.round(s, 3).tolist()}
                  for b, p, s in zip(boxes, kps, scores)]
        if n % 25 == 0:
            print(n, k, len(res[k]), "people", flush=True)
    json.dump(res, open(out, "w"))


def categorise(x, y, people):
    """-> (category, distance to the nearest keypoint of that group or None)."""
    best = None
    for p in people:
        x0, y0, x1, y1 = p["box"]; H = max(y1 - y0, 1.0); lim = max(10.0, 0.1 * H)
        for g, idx in GROUPS.items():
            for i in idx:
                if p["s"][i] < KP_MIN:
                    continue
                d = math.hypot(p["kp"][i][0] - x, p["kp"][i][1] - y)
                if d < lim and (best is None or d < best[1]):
                    best = (g, d)
    if best:
        return best
    for p in people:
        x0, y0, x1, y1 = p["box"]; mx, my = 0.05 * (x1 - x0), 0.05 * (y1 - y0)
        if x0 - mx <= x <= x1 + mx and y0 - my <= y <= y1 + my:
            return "body", None
    return "off-body", None


def wrist_dist(x, y, people):
    d = [math.hypot(p["kp"][i][0] - x, p["kp"][i][1] - y) for p in people for i in GROUPS["hand"] if p["s"][i] >= KP_MIN]
    return min(d, default=1e9)


def stage_report(items_json, labels_dir, tdir, peaks_json, pose_json, sheet):
    items, labels = load(items_json, labels_dir); P = json.load(open(peaks_json)); pose = json.load(open(pose_json))
    pct = lambda a, b: f"{100 * a / b:.0f} %" if b else "-"
    fps = {}
    for model, rows in P["peaks"].items():
        out = []
        for k, l in labels.items():
            for rank, (px, py, s, mv) in enumerate(rows[k]):
                if s < P_MIN or (l["state"] == "ball" and math.hypot(px - l["x"], py - l["y"]) <= R_HIT):
                    continue
                cat, _ = categorise(px, py, pose[k])
                out.append(dict(id=k, x=px, y=py, s=s, rank=rank, static=mv < MOVE_LOCAL, motion=mv, cat=cat,
                                frame=l["state"], clock=items[k]["clock_running"]))
        fps[model] = out
        nb = sum(1 for l in labels.values() if l["state"] == "none")
        print(f"\n== {model}: {len(out)} false peaks >= {P_MIN} ({sum(f['frame'] == 'none' for f in out)} on {nb} no-ball frames,"
              f" {sum(f['frame'] == 'ball' for f in out)} on ball frames)")
        print(f"{'category':9s} {'all':>10s} {'clock on':>10s} {'clock off':>10s} {'no-ball fr':>10s} {'mean s':>7s} {'static':>7s} {'top peak':>8s}")
        on = [f for f in out if f["clock"] is True]; off = [f for f in out if f["clock"] is not True]
        nbf = [f for f in out if f["frame"] == "none"]
        for c in CATS:
            fc = [f for f in out if f["cat"] == c]
            print(f"{c:9s} {len(fc):3d} {pct(len(fc), len(out)):>6s} {pct(sum(f['cat'] == c for f in on), len(on)):>10s}"
                  f" {pct(sum(f['cat'] == c for f in off), len(off)):>10s} {pct(sum(f['cat'] == c for f in nbf), len(nbf)):>10s}"
                  f" {np.mean([f['s'] for f in fc]) if fc else 0:7.2f} {pct(sum(f['static'] for f in fc), len(fc)):>7s}"
                  f" {sum(f['rank'] == 0 for f in fc):8d}")
        print(f"clock on {len(on)}, off/unknown {len(off)}; static overall {pct(sum(f['static'] for f in out), len(out))}")
        tops = [f for f in nbf if f["rank"] == 0 and f["s"] >= 0.5]
        print(f"no-ball frames with top peak >= 0.5: {len(tops)}; their category:",
              dict(collections.Counter(f["cat"] for f in tops)), "static", sum(f["static"] for f in tops))
        # human OWL tags: they describe OWLv2's top box; compare only where our peak is within 12 px of it
        agree = []
        for f in out:
            l = labels[f["id"]]; o = items[f["id"]]["owl"]
            if l.get("owl_fp") and o and math.hypot(o[0][0] - f["x"], o[0][1] - f["y"]) <= R_HIT:
                agree.append((f["id"], l["owl_fp"], f["cat"]))
        print("vs human owl_fp tags (peak within 12 px of OWL top box):", agree)
        miss = [f for f in out if f["frame"] == "ball" and f["rank"] == 0]
        print(f"ball frames whose top peak is a false peak >= {P_MIN}: {len(miss)};", dict(collections.Counter(f["cat"] for f in miss)))
        for name, rule in (("static", lambda f: f["static"]), ("wrist <= 15 px", lambda f: f["wd"] <= 15),
                           ("static and off-body", lambda f: f["static"] and f["cat"] == "off-body")):
            for f in out:
                f.setdefault("wd", wrist_dist(f["x"], f["y"], pose[f["id"]]))
            print(f"filter {name:20s}: removes {pct(sum(map(rule, out)), len(out))} of the false peaks")
    # true balls: how many would a hand filter kill, how many are static
    balls = {k: l for k, l in labels.items() if l["state"] == "ball"}
    wd = [wrist_dist(l["x"], l["y"], pose[k]) for k, l in balls.items()]
    cats = collections.Counter(categorise(l["x"], l["y"], pose[k])[0] for k, l in balls.items())
    bm = P["ball_motion"]
    print(f"\ntrue balls {len(balls)}: within 15 px of a wrist {sum(d <= 15 for d in wd)} ({pct(sum(d <= 15 for d in wd), len(balls))}),"
          f" within 25 px {sum(d <= 25 for d in wd)}; category by the same rule: {dict(cats)};"
          f" static (motion < {MOVE_LOCAL}) {sum(bm[k] < MOVE_LOCAL for k in balls)} ({pct(sum(bm[k] < MOVE_LOCAL for k in balls), len(balls))}),"
          f" static and off-body {sum(bm[k] < MOVE_LOCAL and categorise(l['x'], l['y'], pose[k])[0] == 'off-body' for k, l in balls.items())}")
    for c in CATS:
        ks = [k for k, l in balls.items() if categorise(l["x"], l["y"], pose[k])[0] == c]
        print(f"  true balls {c:9s} {len(ks):3d}, clock on {sum(items[k]['clock_running'] is True for k in ks)}")
    # contact sheet: last model, up to 8 crops per category, spread evenly over the sorted list
    model = list(fps)[-1]; pick = []
    for c in CATS:
        fc = sorted([f for f in fps[model] if f["cat"] == c], key=lambda f: (f["id"], f["rank"]))
        if fc:
            pick += [fc[int(i)] for i in np.unique(np.linspace(0, len(fc) - 1, min(8, len(fc))).round())]
    C, S = 112, 200; tiles = []
    for n, f in enumerate(pick):
        img = triplet(items, tdir, f["id"])[1]; H, W = img.shape[:2]
        x0 = int(np.clip(f["x"] - C // 2, 0, W - C)); y0 = int(np.clip(f["y"] - C // 2, 0, H - C))
        t = cv2.resize(img[y0:y0 + C, x0:x0 + C], (S, S), interpolation=cv2.INTER_CUBIC)
        cx, cy = int((f["x"] - x0) * S / C), int((f["y"] - y0) * S / C)
        cv2.circle(t, (cx, cy), 18, (0, 255, 255), 1)
        txt = f"{n} {f['cat']} {f['s']:.2f}{' ST' if f['static'] else ''}"
        cv2.rectangle(t, (0, 0), (S, 20), (0, 0, 0), -1); cv2.putText(t, txt, (3, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        tiles.append(t); print("sheet", n, f["id"], f["cat"], f["s"], f["frame"], "static" if f["static"] else "")
    cols = 8; rows_ = math.ceil(len(tiles) / cols)
    grid = np.zeros((rows_ * S, cols * S, 3), np.uint8)
    for n, t in enumerate(tiles):
        grid[(n // cols) * S:(n // cols + 1) * S, (n % cols) * S:(n % cols + 1) * S] = t
    cv2.imwrite(sheet, grid, [cv2.IMWRITE_JPEG_QUALITY, 88]); print("sheet:", sheet)
    json.dump(fps, open(Path(sheet).with_suffix(".json"), "w"))


if __name__ == "__main__":
    {"peaks": stage_peaks, "pose": stage_pose, "report": stage_report}[sys.argv[1]](*sys.argv[2:])

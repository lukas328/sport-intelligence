"""Training crops for the ball verifier (re-scores the heatmap net's top-5 peaks). CPU only.

Input: the round 7 OWL tiles (meta_owl.json + img/*.jpg; 224 px triplets, three frames side by side,
`ball` = [x, y, w] in the tile or null). Three stages, because the net needs torch and the pose
model needs rtmlib/onnxruntime (two venvs):

    # 1. top-5 peaks of the heatmap net on every tile (torch venv)
    python ml/ball/verifier/data.py peaks TILES_DIR MODEL.pt PEAKS.json
    # 2. RTMPose people on the centre frame of a subset of tiles (rtmlib venv, Apache-2.0)
    python ml/ball/verifier/data.py pose TILES_DIR POSE.json [MAX_TILES]
    # 3. crops (any venv with opencv + numpy)
    python ml/ball/verifier/data.py crops TILES_DIR PEAKS.json POSE.json CROPS.npz

Crops are STORE x STORE px (72) around a point, three frames stacked (9 channels, RGB); the trainer
cuts 64 px with a random shift. Kinds:
  pos       the OWL-confirmed ball
  pos_peak  a net peak within 12 px of the ball (the offsets the verifier will see at test time)
  neg_peak  a net peak (top 5, score >= 0.05) more than 20 px from the ball (12 to 20 px: skipped)
  neg_hand / neg_head / neg_torso   RTMPose wrist / nose / shoulder-hip centre, no ball within 20 px
  neg_bg    one random point per tile, no ball within 20 px
  neg_static  the ball-like fixed spot (OWLv2 box that never moves) a no-ball tile was cut around
Validation games: crc32(game) % 8 == 0 (whole games, about one in eight).
"""
import json, math, sys, zlib
from pathlib import Path

import cv2, numpy as np

STORE, R_POS, R_NEG, P_MIN, KP_MIN = 72, 12, 20, 0.05, 0.3


def game_of(m):
    return m["src"][4:] if m["src"].startswith("owl_") else m["src"]


def is_val(game):
    return zlib.crc32(game.encode()) % 8 == 0


def read_tile(tdir, m):
    t = cv2.cvtColor(cv2.imread(str(Path(tdir) / "img" / m["file"])), cv2.COLOR_BGR2RGB); w = t.shape[1] // 3
    return np.concatenate([t[:, 0:w], t[:, w:2 * w], t[:, 2 * w:3 * w]], 2)  # H x W x 9


def crop9(img, x, y, s=STORE):
    """s x s crop centred on (x, y); outside the image is reflected (the same at train and test time)."""
    h = s // 2; p = s
    outs = []
    for j in range(img.shape[2] // 3):
        pad = cv2.copyMakeBorder(np.ascontiguousarray(img[:, :, 3 * j:3 * j + 3]), p, p, p, p, cv2.BORDER_REFLECT_101)
        xi, yi = int(round(x)) + p - h, int(round(y)) + p - h
        outs.append(pad[yi:yi + s, xi:xi + s])
    return np.concatenate(outs, 2)


def stage_peaks(tdir, model, out):
    import torch
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from bench_testset2 import BallNet3, peaks
    torch.set_num_threads(4)
    meta = json.load(open(Path(tdir) / "meta_owl.json"))
    net = BallNet3(); net.load_state_dict(torch.load(model, map_location="cpu", weights_only=True)); net.eval()
    res = {}
    for n in range(0, len(meta), 32):
        batch = meta[n:n + 32]
        x = torch.from_numpy(np.stack([read_tile(tdir, m) for m in batch]).transpose(0, 3, 1, 2).astype(np.float32))
        with torch.no_grad():
            hm = torch.sigmoid(net(x))[:, 0].numpy()
        for m, h in zip(batch, hm):
            res[m["file"]] = [[int(px), int(py), round(s, 4)] for px, py, s in peaks(h)]
        if n % 1600 == 0:
            print(n, len(meta), flush=True)
    json.dump(res, open(out, "w"))


def stage_pose(tdir, out, max_tiles=4000):
    from rtmlib import Body  # RTMPose + YOLOX person detector, ONNX on CPU
    body = Body(mode="balanced", backend="onnxruntime", device="cpu")
    meta = json.load(open(Path(tdir) / "meta_owl.json"))
    # deterministic order: all no-ball tiles first (few), then positive tiles by hash
    meta.sort(key=lambda m: (m["ball"] is not None, zlib.crc32(m["file"].encode())))
    res = {}
    for n, m in enumerate(meta[:int(max_tiles)]):
        t = cv2.imread(str(Path(tdir) / "img" / m["file"])); w = t.shape[1] // 3; img = np.ascontiguousarray(t[:, w:2 * w])
        boxes = body.det_model(img)
        kps, scores = body.pose_model(img, bboxes=boxes) if len(boxes) else (np.zeros((0, 17, 2)), np.zeros((0, 17)))
        res[m["file"]] = [{"box": [round(float(v), 1) for v in b[:4]], "kp": np.round(p, 1).tolist(), "s": np.round(s, 3).tolist()}
                          for b, p, s in zip(boxes, kps, scores)]
        if n % 250 == 0:
            print(n, m["file"], len(res[m["file"]]), "people", flush=True)
            json.dump(res, open(out, "w"))
    json.dump(res, open(out, "w"))


def pose_points(people, T):
    """(kind, x, y) for wrists, noses and torso centres with keypoint score >= KP_MIN inside the tile."""
    out = []
    for p in people:
        kp, s = p["kp"], p["s"]
        for i in (9, 10):
            if s[i] >= KP_MIN:
                out.append(("neg_hand", *kp[i]))
        if s[0] >= KP_MIN:
            out.append(("neg_head", *kp[0]))
        tor = [kp[i] for i in (5, 6, 11, 12) if s[i] >= KP_MIN]
        if len(tor) == 4:
            out.append(("neg_torso", sum(q[0] for q in tor) / 4, sum(q[1] for q in tor) / 4))
    return [(k, x, y) for k, x, y in out if 0 <= x < T and 0 <= y < T]


def stage_crops(tdir, peaks_json, pose_json, out):
    meta = json.load(open(Path(tdir) / "meta_owl.json")); P = json.load(open(peaks_json)); pose = json.load(open(pose_json))
    rng = np.random.default_rng(0)
    X, kind, game, val, src_file = [], [], [], [], []
    def add(img, x, y, k, m):
        X.append(crop9(img, x, y)); kind.append(k); g = game_of(m); game.append(g); val.append(is_val(g)); src_file.append(m["file"])
    for n, m in enumerate(meta):
        img = read_tile(tdir, m); T = img.shape[0]; b = m["ball"]
        far = lambda x, y: b is None or math.hypot(x - b[0], y - b[1]) > R_NEG
        if b is not None:
            add(img, b[0], b[1], "pos", m)
        for px, py, s in P[m["file"]]:
            d = math.hypot(px - b[0], py - b[1]) if b is not None else 1e9
            if d <= R_POS:
                add(img, px, py, "pos_peak", m)
            elif d > R_NEG and s >= P_MIN:
                add(img, px, py, "neg_peak", m)
        if m.get("owl_static"):
            add(img, *m["owl_static"], "neg_static", m)
        for k, x, y in pose_points(pose.get(m["file"], []), T):
            if far(x, y):
                add(img, x, y, k, m)
        for _ in range(20):
            x, y = rng.uniform(0, T), rng.uniform(0, T)
            if far(x, y):
                add(img, x, y, "neg_bg", m); break
        if n % 2000 == 0:
            print(n, len(meta), len(X), flush=True)
    kind = np.array(kind); val = np.array(val)
    for k in sorted(set(kind)):
        print(f"{k:10s} train {int(((kind == k) & ~val).sum()):6d}  val {int(((kind == k) & val).sum()):5d}")
    print("val games:", sorted({g for g, v in zip(game, val) if v}))
    np.savez(out, X=np.stack(X), kind=kind, game=np.array(game), val=val, tile=np.array(src_file))


if __name__ == "__main__":
    {"peaks": stage_peaks, "pose": stage_pose, "crops": stage_crops}[sys.argv[1]](*sys.argv[2:])

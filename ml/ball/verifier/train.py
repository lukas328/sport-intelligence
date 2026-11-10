"""Train the ball verifier (ball / no ball on a 64 px, 3-frame crop) on CPU.

    python ml/ball/verifier/train.py CROPS.npz OUT.pt [MINUTES=45] [ARCH=small]

CROPS.npz from data.py. Balanced batches: half positives (confirmed ball, net peaks on the ball),
half negatives (net peaks off the ball, RTMPose hands/heads/torsos, fixed ball-like spots, random background), mixed by
fixed shares. Augmentation: random 64 px cut of the 72 px crop (shift up to 4 px), horizontal
flip, time reversal, brightness/contrast, colour mixing near identity (hue/saturation), motion
blur, noise. Validation on whole held-out games; the checkpoint with the best mean AUC of
positives against net peaks and against hands is kept.
"""
import math, sys, time

import cv2, numpy as np, torch, torch.nn as nn, torch.nn.functional as F

C, BS, EVAL = 64, 128, 250
SHARES = {"pos": 0.3, "pos_peak": 0.2, "neg_peak": 0.2, "neg_hand": 0.12, "neg_head": 0.04, "neg_torso": 0.04, "neg_bg": 0.05,
          "neg_static": 0.05}


class Verifier(nn.Module):
    """Small VGG-style net: 9 x 64 x 64 -> logit."""
    def __init__(s, w=16):
        super().__init__()
        def blk(a, b):
            return nn.Sequential(nn.Conv2d(a, b, 3, padding=1, bias=False), nn.BatchNorm2d(b), nn.ReLU(inplace=True),
                                 nn.Conv2d(b, b, 3, padding=1, bias=False), nn.BatchNorm2d(b), nn.ReLU(inplace=True))
        first = nn.Sequential(nn.Conv2d(9, w, 3, padding=1, bias=False), nn.BatchNorm2d(w), nn.ReLU(inplace=True))
        s.f = nn.Sequential(first, nn.MaxPool2d(2), blk(w, 2 * w), nn.MaxPool2d(2), blk(2 * w, 4 * w), nn.MaxPool2d(2),
                            blk(4 * w, 4 * w))
        s.head = nn.Sequential(nn.Dropout(0.2), nn.Linear(8 * w, 1))

    def forward(s, x):  # x: uint8-range float, N x 9 x 64 x 64
        h = s.f(x / 255.0 - 0.5)
        # global average plus a centre read-out (the ball should be in the middle)
        c = h[:, :, h.shape[2] // 2 - 1:h.shape[2] // 2 + 1, h.shape[3] // 2 - 1:h.shape[3] // 2 + 1].mean((2, 3))
        return s.head(torch.cat([h.mean((2, 3)), c], 1))[:, 0]


def centre(X, c=C):
    o = (X.shape[1] - c) // 2
    return X[:, o:o + c, o:o + c]


def augment(x, rng):
    """x: 72 x 72 x 9 uint8 -> 64 x 64 x 9 float32."""
    s = x.shape[0] - C; dx, dy = rng.integers(0, s + 1, 2)
    y = x[dy:dy + C, dx:dx + C].astype(np.float32)
    if rng.random() < 0.5:
        y = y[:, ::-1]
    if rng.random() < 0.5:
        y = y[:, :, [6, 7, 8, 3, 4, 5, 0, 1, 2]]
    y = np.ascontiguousarray(y).reshape(C, C, 3, 3)  # H W frame rgb
    M = np.eye(3, dtype=np.float32) + rng.normal(0, 0.06, (3, 3)).astype(np.float32)
    y = y @ M.T * rng.uniform(0.7, 1.3) + rng.uniform(-25, 25)
    m = y.mean(); y = (y - m) * rng.uniform(0.75, 1.25) + m
    y = y.reshape(C, C, 9)
    if rng.random() < 0.35:
        L = int(rng.integers(3, 10)); k = np.zeros((L, L), np.float32); k[L // 2] = 1.0
        R = cv2.getRotationMatrix2D(((L - 1) / 2, (L - 1) / 2), float(rng.uniform(0, 180)), 1.0)
        k = cv2.warpAffine(k, R, (L, L)); k /= max(k.sum(), 1e-6)
        y = np.concatenate([cv2.filter2D(np.ascontiguousarray(y[:, :, 3 * j:3 * j + 3]), -1, k) for j in range(3)], 2)
    if rng.random() < 0.3:
        y = y + rng.normal(0, rng.uniform(2, 8), y.shape).astype(np.float32)
    return np.clip(y, 0, 255)


def auc(pos, neg):
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    s = np.concatenate([pos, neg]); r = s.argsort().argsort() + 1.0
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


@torch.no_grad()
def predict(net, X, bs=512):
    net.eval(); out = []
    for i in range(0, len(X), bs):
        out.append(torch.sigmoid(net(torch.from_numpy(X[i:i + bs].transpose(0, 3, 1, 2).astype(np.float32)))).numpy())
    return np.concatenate(out) if out else np.zeros(0)


def main():
    crops, out = sys.argv[1], sys.argv[2]
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 45.0
    torch.manual_seed(0); torch.set_num_threads(4); rng = np.random.default_rng(0)
    d = np.load(crops); X, kind, val = d["X"], d["kind"], d["val"]
    tr = {k: np.where((kind == k) & ~val)[0] for k in SHARES}
    va = np.where(val)[0]; Xv = centre(X[va]); kv = kind[va]
    print({k: len(v) for k, v in tr.items()}, "val", len(va), flush=True)
    keys = [k for k in SHARES if len(tr[k])]; p = np.array([SHARES[k] for k in keys]); p /= p.sum()
    net = Verifier(); opt = torch.optim.AdamW(net.parameters(), lr=2e-3, weight_decay=1e-4)
    t0 = time.time(); step = 0; best = -1.0; hist = []
    # step budget from a timing of the first EVAL steps
    total = None
    while True:
        net.train()
        ks = rng.choice(len(keys), BS, p=p)
        idx = [tr[keys[k]][rng.integers(len(tr[keys[k]]))] for k in ks]
        yb = torch.tensor([keys[k].startswith("pos") for k in ks], dtype=torch.float32)
        xb = torch.from_numpy(np.stack([augment(X[i], rng) for i in idx]).transpose(0, 3, 1, 2).copy())
        if total is not None:
            for g in opt.param_groups:
                g["lr"] = 2e-3 * 0.5 * (1 + math.cos(math.pi * min(step / total, 1.0)))
        loss = F.binary_cross_entropy_with_logits(net(xb), yb)
        opt.zero_grad(); loss.backward(); opt.step(); step += 1
        if step % EVAL == 0:
            el = time.time() - t0
            if total is None:
                total = int(minutes * 60 / (el / step) * 0.9); print("planned steps", total, flush=True)
            pr = predict(net, Xv); pos = pr[np.char.startswith(kv.astype(str), "pos")]
            a = {k: round(auc(pos, pr[kv == k]), 4) for k in SHARES if not k.startswith("pos")}
            score = (a["neg_peak"] + a["neg_hand"]) / 2
            hist.append((step, round(loss.item(), 4), a))
            print(f"step {step} {el / 60:.1f} min loss {loss.item():.3f} val AUC {a} mean(peak,hand) {score:.4f}", flush=True)
            if score > best:
                best = score; torch.save(net.state_dict(), out)
            if step >= total:
                break
    print("best", best, "saved", out)


if __name__ == "__main__":
    main()

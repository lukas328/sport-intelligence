"""Holder classifier: does this player hold the ball? ResNet18 (ImageNet) on a player crop.

  --ch 9: the three frames t-G, t, t+G stacked (conv1: centre frame gets the pretrained weights,
          the neighbours start at 0), --ch 3: centre frame only.
  --aux W: auxiliary ball heatmap (stride 8, from layer2) on every crop whose rectangle contains
          the clicked ball, holder or not, CenterNet focal loss with weight W. Dense supervision
          tells the net *where* to look instead of letting it memorise poses.
  --extra DIR: more training crops (build_rf_crops.py: still frames, repeated for t-G and t+G).
Balanced batches (half positives), augmentations that keep the geometry: horizontal flip, time
reversal, a small random crop/shift, brightness/contrast/saturation and a small hue shift (the
ball's colour matters, so no full hue rotation). Fixed number of steps, one-cycle LR, no model
selection on the test data. Writes <out>/model.pt and <out>/pred.json (test predictions).

usage: train.py <data dir> <out dir> [--ch 9] [--size 96] [--steps 1200] [--aux 1] [--extra DIR]
  --all: train on every split except the benchmark test half of the single frames (final model)
"""

import argparse
import json
import random
import time
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision

ap = argparse.ArgumentParser()
ap.add_argument("data")
ap.add_argument("out")
ap.add_argument("--ch", type=int, default=9)
ap.add_argument("--size", type=int, default=96, help="crop width; height is twice that")
ap.add_argument("--steps", type=int, default=1200)
ap.add_argument("--batch", type=int, default=32)
ap.add_argument("--lr", type=float, default=3e-4)
ap.add_argument("--aux", type=float, default=0.0)
ap.add_argument("--extra", action="append", default=[])
ap.add_argument("--extra-frac", type=float, default=0.5, help="share of a batch drawn from --extra")
ap.add_argument("--threads", type=int, default=3)
ap.add_argument("--no-interp", action="store_true", help="drop the interpolated in-between frames")
ap.add_argument("--all", action="store_true")
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()
torch.set_num_threads(args.threads)
random.seed(args.seed)
np.random.seed(args.seed)
torch.manual_seed(args.seed)
D, OUT = Path(args.data), Path(args.out)
OUT.mkdir(parents=True, exist_ok=True)
W, H = args.size, args.size * 2
STRIDE = 8

meta = [m | {"_dir": str(D)} for m in json.load(open(D / "meta.json"))]
if args.all:
    tr = [m for m in meta if not (m["src"] == "single" and m["split"] == "test")]
else:
    tr = [m for m in meta if m["split"] == "train"]
if args.no_interp:
    tr = [m for m in tr if m["kind"] != "interp"]
te = [m for m in meta if m["split"] == "test" and m["kind"] != "interp"]
ex = [m | {"_dir": e} for e in args.extra for m in json.load(open(Path(e) / "meta.json"))]


class Net(nn.Module):
    def __init__(self, ch, aux):
        super().__init__()
        r = torchvision.models.resnet18(weights=torchvision.models.ResNet18_Weights.IMAGENET1K_V1)
        if ch == 9:
            w = r.conv1.weight.data
            c = nn.Conv2d(9, 64, 7, 2, 3, bias=False)
            c.weight.data = torch.cat([torch.zeros_like(w), w, torch.zeros_like(w)], 1)
            r.conv1 = c
        r.fc = nn.Linear(512, 1)
        self.r = r
        self.hm = None
        if aux:
            self.hm = nn.Sequential(nn.Conv2d(128, 64, 3, padding=1), nn.ReLU(), nn.Conv2d(64, 1, 1))
            self.hm[-1].bias.data.fill_(-4.0)

    def forward(self, x):
        r = self.r
        x = r.maxpool(r.relu(r.bn1(r.conv1(x))))
        f2 = r.layer2(r.layer1(x))
        logit = r.fc(torch.flatten(r.avgpool(r.layer4(r.layer3(f2))), 1))[:, 0]
        return logit, (self.hm(f2)[:, 0] if self.hm is not None else None)


MEAN = torch.tensor([0.485, 0.456, 0.406] * 3).view(1, 9, 1, 1) * 255
STD = torch.tensor([0.229, 0.224, 0.225] * 3).view(1, 9, 1, 1) * 255


def load(m, aug):
    """Crop (H x W x ch float) and the ball in crop pixels (None: not in the crop)."""
    t = cv2.cvtColor(cv2.imread(str(Path(m["_dir"]) / "crops" / m["file"])), cv2.COLOR_BGR2RGB)
    if t.shape[1] * 2 < t.shape[0] * 1.2:  # a still frame: one crop
        fr = [t, t, t]
    else:
        w = t.shape[1] // 3
        fr = [t[:, k * w : (k + 1) * w] for k in range(3)]
    h0, w0 = fr[0].shape[:2]
    ball = None
    if "rect" in m:
        X1, Y1, X2, Y2 = m["rect"]
        bx, by = (m["ball"][0] - X1) / (X2 - X1) * w0, (m["ball"][1] - Y1) / (Y2 - Y1) * h0
        if 0 <= bx < w0 and 0 <= by < h0:
            ball = [bx, by]
    if aug:
        if random.random() < 0.5:
            fr = [f[:, ::-1] for f in fr]
            if ball:
                ball[0] = w0 - ball[0]
        if random.random() < 0.5:
            fr = fr[::-1]
        s = random.uniform(0.88, 1.0)
        h2, w2 = int(h0 * s), int(w0 * s)
        y0, x0 = random.randint(0, h0 - h2), random.randint(0, w0 - w2)
        fr = [f[y0 : y0 + h2, x0 : x0 + w2] for f in fr]
        if ball:
            ball = [(ball[0] - x0) * w0 / w2, (ball[1] - y0) * h0 / h2]
            if not (0 <= ball[0] < w0 and 0 <= ball[1] < h0):
                ball = None
        dh, sat = random.randint(-8, 8), random.uniform(0.7, 1.3)
        g, b = random.uniform(0.7, 1.3), random.uniform(-25, 25)
        out = []
        for f in fr:
            hsv = cv2.cvtColor(np.ascontiguousarray(f), cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[..., 0] = (hsv[..., 0] + dh) % 180
            hsv[..., 1] = np.clip(hsv[..., 1] * sat, 0, 255)
            f = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)
            out.append(np.clip((f - 128) * g + 128 + b, 0, 255))
        fr = out
    fr = [cv2.resize(np.ascontiguousarray(f, dtype=np.float32), (W, H), interpolation=cv2.INTER_AREA) for f in fr]
    if ball:
        ball = (ball[0] * W / w0, ball[1] * H / h0)
    if args.ch == 3:
        fr = [fr[1]]
    return np.concatenate(fr, 2), ball


YY, XX = np.mgrid[0 : H // STRIDE, 0 : W // STRIDE].astype(np.float32) * STRIDE + STRIDE / 2


def batch(ms, aug):
    xs, hms = [], []
    for m in ms:
        x, ball = load(m, aug)
        xs.append(x)
        if ball is None:
            hms.append(np.zeros_like(YY))
        else:
            g = np.exp(-((XX - ball[0]) ** 2 + (YY - ball[1]) ** 2) / (2 * (STRIDE * 0.75) ** 2))
            g[np.unravel_index(g.argmax(), g.shape)] = 1.0
            hms.append(g)
    x = torch.from_numpy(np.stack(xs)).permute(0, 3, 1, 2)
    return (x - MEAN[:, : args.ch]) / STD[:, : args.ch], torch.from_numpy(np.stack(hms))


def focal(logit, gt):
    p = torch.sigmoid(logit).clamp(1e-4, 1 - 1e-4)
    pos = gt.eq(1).float()
    lp = -(torch.log(p) * (1 - p) ** 2 * pos).sum()
    ln = -(torch.log(1 - p) * p**2 * (1 - gt) ** 4 * (1 - pos)).sum()
    return (lp + ln) / pos.sum().clamp(min=1)


def predict(model, ms):
    model.eval()
    ps = []
    with torch.no_grad():
        for k in range(0, len(ms), 64):
            ps += torch.sigmoid(model(batch(ms[k : k + 64], False)[0])[0]).tolist()
    model.train()
    return ps


def quick(ps, ms):
    pos = np.array([p for m, p in zip(ms, ps) if m["y"]])
    neg = np.array([p for m, p in zip(ms, ps) if not m["y"]])
    auc = float((pos[:, None] > neg[None]).mean() + 0.5 * (pos[:, None] == neg[None]).mean())
    by = {}
    for m, p in zip(ms, ps):
        by.setdefault(m["frame"], []).append((p, m["y"]))
    hf = [v for v in by.values() if any(y for _, y in v)]
    top = float(np.mean([max(v)[1] == 1 for v in hf]))
    return f"auc {auc:.3f} top {top:.3f} ({len(hf)} frames)"


if __name__ == "__main__":
    model = Net(args.ch, args.aux)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, args.lr, total_steps=args.steps, pct_start=0.1)
    pos = [m for m in tr if m["y"]]
    neg = [m for m in tr if not m["y"]]
    xpos = [m for m in ex if m["y"]]
    xneg = [m for m in ex if not m["y"]]
    print(f"train {len(pos)} pos {len(neg)} neg, extra {len(xpos)} pos {len(xneg)} neg, test {sum(m['y'] for m in te)} pos {len(te)} crops", flush=True)
    t0, run = time.time(), []
    half = args.batch // 2
    nx = round(half * args.extra_frac) if ex else 0
    for step in range(1, args.steps + 1):
        ms = random.choices(pos, k=half - nx) + random.choices(xpos, k=nx) if nx else random.choices(pos, k=half)
        ms += random.choices(neg, k=half - nx) + random.choices(xneg, k=nx) if nx else random.choices(neg, k=half)
        y = torch.tensor([m["y"] for m in ms], dtype=torch.float32)
        x, hm = batch(ms, True)
        logit, hlog = model(x)
        loss = F.binary_cross_entropy_with_logits(logit, y)
        if args.aux:
            loss = loss + args.aux * focal(hlog, hm)
        opt.zero_grad()
        loss.backward()
        opt.step()
        sched.step()
        run.append(loss.item())
        if step % 100 == 0:
            msg = f"step {step} loss {np.mean(run[-100:]):.3f} {time.time() - t0:.0f}s"
            if step % 400 == 0 or step == args.steps:
                msg += " | test " + quick(predict(model, te), te)
            print(msg, flush=True)
    torch.save({"state": model.state_dict(), "ch": args.ch, "w": W, "h": H, "aux": args.aux}, OUT / "model.pt")
    ps = predict(model, te)
    json.dump([{"file": m["file"], "p": round(p, 4)} for m, p in zip(te, ps)], open(OUT / "pred.json", "w"))
    print("done", quick(ps, te), f"{time.time() - t0:.0f}s", flush=True)

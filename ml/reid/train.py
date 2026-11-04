"""Train the handball re-identification model on shirt-number-labelled crops (build_dataset.py).

ResNet18 (ImageNet) + 256-d BNNeck embedding; loss = batch-hard triplet (on the feature) +
label-smoothed identity cross-entropy (on the BN feature). Batches are P identities x K crops
drawn from one clip and team (all shirts equal: the model has to use hair, build, skin, shoes),
plus a second clip-team group; triplet negatives are only taken within a clip (the same club can
appear in two clips with the same players).

Run with the torch environment:

    python ml/reid/train.py --data <dataset dir> --test-clip <clip or none> --out model.pt
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F  # noqa: N812

sys.path.insert(0, str(Path(__file__).parent))
from common import build_model, clean, load_index  # noqa: E402


def augment(img: np.ndarray, size: tuple[int, int], rng: random.Random) -> np.ndarray:
    """img: 256 x 128 RGB uint8 -> size (H, W) float32 RGB 0..255."""
    h, w = img.shape[:2]
    if rng.random() < 0.5:
        img = img[:, ::-1]
    # random crop (scale 0.8..1 of each side) with a little translation
    sh, sw = rng.uniform(0.8, 1.0), rng.uniform(0.8, 1.0)
    ch, cw = int(h * sh), int(w * sw)
    y0, x0 = rng.randint(0, h - ch), rng.randint(0, w - cw)
    img = img[y0 : y0 + ch, x0 : x0 + cw]
    # low resolution like distant players: down to 40..100 % then back up
    if rng.random() < 0.5:
        f = rng.uniform(0.4, 1.0)
        img = cv2.resize(img, (max(8, int(cw * f)), max(16, int(ch * f))), cv2.INTER_AREA)
    if rng.random() < 0.2:
        img = cv2.GaussianBlur(img, (0, 0), rng.uniform(0.5, 1.5))
    out = cv2.resize(np.ascontiguousarray(img), (size[1], size[0]), cv2.INTER_LINEAR)
    out = out.astype(np.float32)
    # colour: brightness/contrast/saturation, hue almost untouched (kit colour separates teams)
    out = out * rng.uniform(0.75, 1.25) + rng.uniform(-20, 20)
    mean = out.mean()
    out = (out - mean) * rng.uniform(0.8, 1.2) + mean
    grey = out.mean(axis=2, keepdims=True)
    out = grey + (out - grey) * rng.uniform(0.8, 1.2)
    if rng.random() < 0.4:  # random erasing
        eh, ew = int(size[0] * rng.uniform(0.1, 0.4)), int(size[1] * rng.uniform(0.1, 0.4))
        ey, ex = rng.randint(0, size[0] - eh), rng.randint(0, size[1] - ew)
        out[ey : ey + eh, ex : ex + ew] = rng.uniform(0, 255)
    return np.clip(out, 0, 255)


def batch_hard(
    f: torch.Tensor,
    ids: torch.Tensor,
    clips: torch.Tensor,
    numbered: torch.Tensor,
    spans: torch.Tensor,
    margin: float,
):
    """Negatives: other identities of the same clip that are known to be other people: both
    numbered (different numbers), or on court at the same time (track spans overlap by 2 s)."""
    d = torch.cdist(f, f)
    same = ids[:, None] == ids[None, :]
    overlap = torch.minimum(spans[:, None, 1], spans[None, :, 1]) - torch.maximum(
        spans[:, None, 0], spans[None, :, 0]
    )
    known = (numbered[:, None] & numbered[None, :]) | (overlap > 60)
    neg_ok = (~same) & (clips[:, None] == clips[None, :]) & known
    eye = torch.eye(len(f), dtype=torch.bool)
    pos = torch.where(same & ~eye, d, torch.zeros_like(d)).max(1).values
    neg = torch.where(neg_ok, d, torch.full_like(d, 1e4)).min(1).values
    valid = (same & ~eye).any(1) & neg_ok.any(1)
    loss = F.relu(pos - neg + margin)[valid]
    return loss.mean() if len(loss) else f.sum() * 0, (pos < neg)[valid].float().mean()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--test-clip", default="none")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--iters", type=int, default=1500)
    ap.add_argument("--p", type=int, default=8)
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--groups", type=int, default=2, help="clip-team groups per batch")
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--margin", type=float, default=0.3)
    ap.add_argument("--height", type=int, default=192)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tracklets", action="store_true", help="use unnumbered tracks too")
    ap.add_argument("--tracklet-share", type=float, default=0.5, help="of a batch's identities")
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    torch.manual_seed(a.seed)
    rng = random.Random(a.seed)
    size = (a.height, a.height // 2)

    rows = [r for r in clean(load_index(a.data), a.data) if r["clip"] != a.test_clip]
    if not a.tracklets:
        rows = [r for r in rows if r.get("numbered", True)]
    idents = sorted({r["identity"] for r in rows})
    clip_names = sorted({r["clip"] for r in rows})
    label = {i: k for k, i in enumerate(idents)}
    imgs = np.stack([cv2.imread(str(a.data / r["file"]))[:, :, ::-1] for r in rows])
    by_id: dict[int, list[int]] = defaultdict(list)
    for n, r in enumerate(rows):
        by_id[label[r["identity"]]].append(n)
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    tgroups: dict[tuple[str, str], list[int]] = defaultdict(list)
    span_of: dict[int, list[int]] = {}
    for n, r in enumerate(rows):
        span_of.setdefault(label[r["identity"]], r.get("span", [0, 10**9]))
    for i in idents:
        c, t, num = i.split("/")
        (tgroups if num.startswith("t") else groups)[(c, t)].append(label[i])
    gkeys = [g for g in groups if len(groups[g]) >= 2]
    gweights = [sum(len(by_id[i]) for i in groups[g]) ** 0.5 for g in gkeys]
    print(
        f"train: {len(rows)} crops, {len(idents)} identities "
        f"({sum(len(v) for v in tgroups.values())} tracklets), groups "
        + ", ".join(f"{c[-12:]}/{t}:{len(groups[(c, t)])}" for c, t in gkeys),
        flush=True,
    )

    model = build_model(size=size)
    head = torch.nn.Linear(256, len(idents), bias=False)
    params = list(model.parameters()) + list(head.parameters())
    opt = torch.optim.AdamW([p for p in params if p.requires_grad], lr=a.lr, weight_decay=5e-4)
    warm = max(1, a.iters // 15)

    def lr_at(it: int) -> float:
        if it < warm:
            return (it + 1) / warm
        return 0.5 * (1 + np.cos(np.pi * (it - warm) / max(1, a.iters - warm)))

    sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_at)
    model.train()
    t0 = time.time()
    log_l, log_c, log_acc = [], [], []
    for it in range(a.iters):
        idx: list[int] = []
        for g in rng.choices(gkeys, gweights, k=a.groups):
            ids = groups[g]
            n_t = round(a.p * a.tracklet_share) if tgroups.get(g) else 0
            pick = rng.sample(ids, min(a.p - n_t, len(ids)))
            if n_t:  # tracklets on court around a random numbered crop's time
                ref = span_of[rng.choice(pick)]
                tl = [i for i in tgroups[g] if span_of[i][0] < ref[1] and span_of[i][1] > ref[0]]
                pick += rng.sample(tl, min(n_t, len(tl)))
            for i in pick:
                pool = by_id[i]
                idx += rng.sample(pool, a.k) if len(pool) >= a.k else rng.choices(pool, k=a.k)
        x = np.stack([augment(imgs[n], size, rng) for n in idx]).transpose(0, 3, 1, 2)
        x = torch.from_numpy(np.ascontiguousarray(x))
        y = torch.tensor([label[rows[n]["identity"]] for n in idx])
        cl = torch.tensor([clip_names.index(rows[n]["clip"]) for n in idx])
        f, b = model(x)
        nb = torch.tensor([bool(rows[n].get("numbered", True)) for n in idx])
        sp = torch.tensor([rows[n].get("span", [0, 10**9]) for n in idx])
        tl, acc = batch_hard(f, y, cl, nb, sp, a.margin)
        ce = F.cross_entropy(head(b), y, label_smoothing=0.1)
        loss = tl + ce
        opt.zero_grad()
        loss.backward()
        opt.step()
        sched.step()
        log_l.append(tl.item())
        log_c.append(ce.item())
        log_acc.append(acc.item())
        if (it + 1) % 50 == 0:
            print(
                f"it {it + 1} triplet {np.mean(log_l):.3f} ce {np.mean(log_c):.3f} "
                f"triplet-acc {np.mean(log_acc):.2f} lr {sched.get_last_lr()[0]:.2e} "
                f"{time.time() - t0:.0f}s",
                flush=True,
            )
            log_l, log_c, log_acc = [], [], []
    model.eval()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"state": model.state_dict(), "size": size, "identities": idents, "args": {k: str(v) for k, v in vars(a).items()}},
        a.out,
    )
    print("saved", a.out, f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

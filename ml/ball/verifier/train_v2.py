"""Train verifier v2: v1's crops plus the human-labelled hard peaks (train games only). CPU.

    python ml/ball/verifier/train_v2.py CROPS_CANON.npz HUMAN.npz OUT.pt MODE [MINUTES|steps=N] [INIT.pt|-] [FRAC]

MODE scratch:  new net; batches are 60 % v1 kinds (v1 shares) + 15 % human balls + 25 % human
               "no ball" (the confident round 7 mistakes, strongly up-weighted: 242 crops against
               about 66 000 v1 crops, yet a quarter of every batch).
MODE finetune: start from INIT.pt (v1), lr 5e-4; 25 % human balls + 40 % human "no ball" + 35 % v1.
Augmentation as train.py. The tuning games of HUMAN.npz are never read here. Checkpoints at half
and at the end of the cosine schedule (OUT with _half / no suffix); the choice between them is made
on the tuning set (tune_v2.py), not here. The v1 validation games are logged as a sanity check.
FRAC < 1 (learning curve): keep that share of the human train crops, the same share in every game
(FRAC 0: v1 crops only, the control for the format change and the extra steps).
"""
import math, sys, time

import numpy as np, torch, torch.nn.functional as F

from train import BS, SHARES, Verifier, auc, augment, centre, predict

EVAL = 250


def main():
    crops, human, out, mode = sys.argv[1:5]
    arg = sys.argv[5] if len(sys.argv) > 5 else ("30" if mode == "scratch" else "8")
    fixed = int(arg[6:]) if arg.startswith("steps=") else None; minutes = None if fixed else float(arg)
    init = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] != "-" else None
    frac = float(sys.argv[7]) if len(sys.argv) > 7 else 1.0
    torch.manual_seed(0); torch.set_num_threads(4); rng = np.random.default_rng(0)
    d = np.load(crops); X, kind, val = d["X"], d["kind"], d["val"]
    h = np.load(human); hX, hy, ht = h["X"], h["y"], h["tune"]
    pools = {k: (X, np.where((kind == k) & ~val)[0]) for k in SHARES}
    keep = ~ht
    if frac < 1:
        sub = np.random.default_rng(1); keep = np.zeros(len(hy), bool)
        for g in sorted(set(h["game"][~ht])):
            ix = sub.permutation(np.where((h["game"] == g) & ~ht)[0]); keep[ix[:round(frac * len(ix))]] = True
    pools["h_pos"] = (hX, np.where(hy & keep)[0]); pools["h_neg"] = (hX, np.where(~hy & keep)[0])
    v1w, hp, hn, lr0 = (0.60, 0.15, 0.25, 2e-3) if mode == "scratch" else (0.35, 0.25, 0.40, 5e-4)
    shares = {k: v * v1w for k, v in SHARES.items()} | {"h_pos": hp, "h_neg": hn}
    keys = [k for k in shares if len(pools[k][1])]; p = np.array([shares[k] for k in keys]); p /= p.sum()
    print({k: len(pools[k][1]) for k in keys}, flush=True)
    va = np.where(val)[0]; Xv = centre(X[va]); kv = kind[va]
    net = Verifier()
    if init:
        net.load_state_dict(torch.load(init, map_location="cpu", weights_only=True))
    opt = torch.optim.AdamW(net.parameters(), lr=lr0, weight_decay=1e-4)
    t0 = time.time(); step = 0; total = fixed; half_saved = False
    while True:
        net.train()
        ks = rng.choice(len(keys), BS, p=p)
        xs = []
        for k in ks:
            A, ix = pools[keys[k]]; xs.append(augment(A[ix[rng.integers(len(ix))]], rng))
        yb = torch.tensor([keys[k].startswith("pos") or keys[k] == "h_pos" for k in ks], dtype=torch.float32)
        xb = torch.from_numpy(np.stack(xs).transpose(0, 3, 1, 2).copy())
        if total is not None:
            for g in opt.param_groups:
                g["lr"] = lr0 * 0.5 * (1 + math.cos(math.pi * min(step / total, 1.0)))
        loss = F.binary_cross_entropy_with_logits(net(xb), yb)
        opt.zero_grad(); loss.backward(); opt.step(); step += 1
        if total is None and step == 50:
            total = int(minutes * 60 / ((time.time() - t0) / step) * 0.85); print("planned steps", total, flush=True)
        if total is not None and not half_saved and step >= total // 2:
            torch.save(net.state_dict(), out.replace(".pt", "_half.pt")); half_saved = True
        if step % EVAL == 0 or (total is not None and step >= total):
            pr = predict(net, Xv); pos = pr[np.char.startswith(kv.astype(str), "pos")]
            a = {k: round(auc(pos, pr[kv == k]), 3) for k in ("neg_peak", "neg_hand")}
            print(f"step {step} {(time.time() - t0) / 60:.1f} min loss {loss.item():.3f} v1-val AUC {a}", flush=True)
        if total is not None and step >= total:
            break
    torch.save(net.state_dict(), out); print("saved", out)


if __name__ == "__main__":
    main()

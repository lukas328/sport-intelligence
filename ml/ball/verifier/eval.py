"""Does the verifier help the heatmap net on ball test set 2? (CPU; evaluation only, never train on it)

    python ml/ball/verifier/eval.py ITEMS_JSON LABELS_DIR T_DIR NET.pt VERIFIER.pt PEAKS_CACHE.json [OUT.json]

For every labelled frame: the net's top-5 peaks (as bench_testset2.py; cached in PEAKS_CACHE.json),
the verifier's probability on a 64 px, 3-frame crop around each peak, then the peaks re-ranked by
  net        heatmap score (the baseline)
  verifier   verifier probability alone
  product    heatmap score x verifier probability
  geo        sqrt(heatmap score x verifier probability)
Definitions as bench_testset2.py: hit = within 12 px of the label (1280-wide frame); top1 = the
best re-ranked peak is a hit; top5 = any of the five (the same set for every scorer); score at the
ball = score of the best peak within 12 px (0 if none); no-ball frames: top score >= 0.5. Since the
scores live on different scales, also: balls found (top1 and top score >= t) at the threshold t
where 10 % / 25 % of the no-ball frames raise an alarm. Paired: top-1 balls gained / lost against
the net, exact two-sided McNemar (binomial on the discordant pairs).
"""
import json, math, sys
from pathlib import Path

import cv2, numpy as np, torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
from bench_testset2 import BallNet3, peaks  # noqa: E402
from data import crop9  # noqa: E402
from train import Verifier, predict  # noqa: E402

R_HIT = 12


def load(items_json, labels_dir):
    items = {i["id"]: i for i in json.load(open(items_json))}
    labels = {}
    for f in sorted(Path(labels_dir).glob("*.json")):
        d = json.load(open(f)); labels[f.stem] = d.get("data", d)
    return items, {k: v for k, v in sorted(labels.items()) if v["state"] in ("ball", "none") and k in items}


def frames(items, tdir, k):
    it = items[k]; t = cv2.imread(str(Path(tdir) / f"{it.get('k', k)}.jpg")); W = it["w"]
    return [cv2.cvtColor(t[:, j * W:(j + 1) * W], cv2.COLOR_BGR2RGB) for j in range(3)]


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def frame_stats(r, f):
    sc = f(r); i = int(sc.argmax()); o = {"top": float(sc[i])}
    if r["state"] == "ball":
        d = np.array(r["d"]); hit = d < R_HIT
        o |= {"top1": bool(hit[i]), "top5": bool(hit.any()), "at_ball": float(sc[hit].max()) if hit.any() else 0.0}
    return o


def report(sel, title, scorers):
    print(f"\n== {title}")
    B = [r for r in sel if r["state"] == "ball"]; N = [r for r in sel if r["state"] == "none"]
    print(f"{len(B)} balls, {len(N)} no-ball frames")
    pct = lambda xs: f"{100 * np.mean(xs):5.1f} %" if len(xs) else "    -"
    base = [frame_stats(r, scorers["net"]) for r in B]
    print(f"{'scorer':9s} {'top1':>8s} {'top5':>8s} {'at ball>=0.3':>12s} {'no-ball>=0.5':>12s} {'found@FA10':>11s} {'found@FA25':>11s}"
          f"   paired top1 vs net (gained/lost, McNemar p)")
    for name, f in scorers.items():
        sb = [frame_stats(r, f) for r in B]; sn = [frame_stats(r, f) for r in N]
        tops_n = np.array([x["top"] for x in sn])
        fa = []
        for q in (0.10, 0.25):
            t = np.quantile(tops_n, 1 - q, method="higher") + 1e-9 if len(tops_n) else 0.0
            fa.append(pct([x["top1"] and x["top"] >= t for x in sb]) + f"({100 * np.mean(tops_n >= t):.0f})")
        g = sum(x["top1"] and not y["top1"] for x, y in zip(sb, base)); lo = sum(y["top1"] and not x["top1"] for x, y in zip(sb, base))
        print(f"{name:9s} {pct([x['top1'] for x in sb]):>8s} {pct([x['top5'] for x in sb]):>8s} {pct([x['at_ball'] >= 0.3 for x in sb]):>12s}"
              f" {pct([x['top'] >= 0.5 for x in sn]):>12s} {fa[0]:>11s} {fa[1]:>11s}   +{g} / -{lo}, p = {mcnemar(g, lo):.3f}")


def main():
    items_json, labels_dir, tdir, net_pt, ver_pt, cache = sys.argv[1:7]
    out = sys.argv[7] if len(sys.argv) > 7 else None
    torch.set_num_threads(4)
    items, labels = load(items_json, labels_dir)
    P = json.load(open(cache)) if Path(cache).exists() else {}
    if any(k not in P for k in labels):
        net = BallNet3(); net.load_state_dict(torch.load(net_pt, map_location="cpu", weights_only=True)); net.eval()
        for k in labels:
            if k in P:
                continue
            ims = frames(items, tdir, k); h2, w2 = ims[0].shape[0] // 32 * 32, ims[0].shape[1] // 32 * 32
            x = torch.from_numpy(np.concatenate([i[:h2, :w2] for i in ims], 2).transpose(2, 0, 1)[None].astype(np.float32))
            with torch.no_grad():
                hm = torch.sigmoid(net(x))[0, 0].numpy()
            P[k] = [[int(px), int(py), round(s, 4)] for px, py, s in peaks(hm)]
        json.dump(P, open(cache, "w"))
    ver = Verifier(); ver.load_state_dict(torch.load(ver_pt, map_location="cpu", weights_only=True)); ver.eval()
    rows = []
    for k, l in labels.items():
        img = np.concatenate(frames(items, tdir, k), 2)
        pk = P[k]; v = predict(ver, np.stack([crop9(img, px, py, 64) for px, py, _ in pk]))
        s = np.array([q[2] for q in pk])
        d = np.array([math.hypot(px - l["x"], py - l["y"]) for px, py, _ in pk]) if l["state"] == "ball" else None
        rows.append({"id": k, "state": l["state"], "clock": bool(items[k]["clock_running"]), "s": s.tolist(),
                     "v": v.round(4).tolist(), "d": None if d is None else d.round(1).tolist()})
    if out:
        json.dump(rows, open(out, "w"))
    scorers = {"net": lambda r: np.array(r["s"]), "verifier": lambda r: np.array(r["v"]),
               "product": lambda r: np.array(r["s"]) * np.array(r["v"]), "geo": lambda r: np.sqrt(np.array(r["s"]) * np.array(r["v"]))}

    report(rows, "test set 2, all frames", scorers)
    report([r for r in rows if r["clock"]], "clock running", scorers)
    report([r for r in rows if not r["clock"]], "clock stopped or unknown", scorers)
    # verifier probability by peak kind on the test set (how separable are hits and misses?)
    hits = [v for r in rows if r["state"] == "ball" for v, d in zip(r["v"], r["d"]) if d < R_HIT]
    miss = [v for r in rows for i, v in enumerate(r["v"]) if r["state"] == "none" or r["d"][i] > 20]
    from train import auc
    print(f"\nverifier on test peaks: hits {len(hits)} median {np.median(hits):.2f}; false peaks (> 20 px or no-ball frame) {len(miss)}"
          f" median {np.median(miss):.2f}; AUC {auc(np.array(hits), np.array(miss)):.3f}")
    hs = [s for r in rows if r["state"] == "ball" for s, d in zip(r["s"], r["d"]) if d < R_HIT]
    ms = [s for r in rows for i, s in enumerate(r["s"]) if r["state"] == "none" or r["d"][i] > 20]
    print(f"net score on the same peaks: AUC {auc(np.array(hs), np.array(ms)):.3f}")


if __name__ == "__main__":
    main()

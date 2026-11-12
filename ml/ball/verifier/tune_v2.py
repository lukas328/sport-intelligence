"""Choose verifier and combination rule on the human-labelled TUNING games only (never test set 2).

    python ml/ball/verifier/tune_v2.py HUMAN.npz CHOICE.json name=VERIFIER.pt [name=VERIFIER.pt ...]

Population: round 7 peaks with score >= 0.4 (top 3 per frame) in the tuning games, labelled ball /
no ball. Per verifier and rule: AUC (ball vs no ball), precision at 80 % and 90 % recall of the
balls, game-cluster bootstrap 95 % interval of the AUC. Rules (s = net score, v = verifier):
  net s | verifier v | product s*v | geo25 s^0.25 v^0.75 | geo75 s^0.75 v^0.25
  gate  s if v >= t else 0.1 s, t = the v that keeps 90 % of the tuning balls
The pair with the highest AUC is written to CHOICE.json (frozen before the test set 2 run).
"""
import json, sys

import numpy as np, torch

from train import Verifier, auc, centre, predict


def rule_scores(name, s, v, t=None):
    return {"net": s, "verifier": v, "product": s * v, "geo25": s ** 0.25 * v ** 0.75, "geo75": s ** 0.75 * v ** 0.25,
            "gate": np.where(v >= (t if t is not None else 0.5), s, 0.1 * s)}[name]


def prec_at_recall(y, sc, r):
    o = np.argsort(-sc, kind="stable"); tp = np.cumsum(y[o]); k = int(np.searchsorted(tp, np.ceil(r * y.sum())))
    return float(tp[k] / (k + 1))


def main():
    human, out = sys.argv[1:3]; models = dict(a.split("=", 1) for a in sys.argv[3:])
    torch.set_num_threads(4)
    h = np.load(human); m = h["tune"]; X = centre(h["X"][m], 64); y = h["y"][m].astype(bool); s = h["score"][m].astype(np.float64)
    games = h["game"][m]; ug = sorted(set(games)); rng = np.random.default_rng(0)
    boot = [np.concatenate([np.where(games == ug[i])[0] for i in rng.integers(len(ug), size=len(ug))]) for _ in range(1000)]
    print(f"tuning set: {len(ug)} games, {int(y.sum())} balls, {int((~y).sum())} no ball (peaks >= 0.4)")
    print(f"{'model':10s} {'rule':9s} {'AUC':>6s} {'95% CI':>13s} {'P@R80':>6s} {'P@R90':>6s}")
    best, rows = None, []
    for name, path in models.items():
        net = Verifier(); net.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        v = predict(net, X).astype(np.float64); t = float(np.quantile(v[y], 0.10))
        for rule in ("net", "verifier", "product", "geo25", "geo75", "gate"):
            if rule == "net" and rows:
                continue
            sc = rule_scores(rule, s, v, t); a = auc(sc[y], sc[~y])
            bs = [auc(sc[b][y[b]], sc[b][~y[b]]) for b in boot]; lo, hi = np.nanpercentile(bs, [2.5, 97.5])
            r = {"model": name if rule != "net" else "-", "path": path, "rule": rule, "t": t if rule == "gate" else None,
                 "auc": a, "ci": [lo, hi], "p80": prec_at_recall(y, sc, 0.8), "p90": prec_at_recall(y, sc, 0.9)}
            rows.append(r)
            print(f"{r['model']:10s} {rule:9s} {a:6.3f} [{lo:.3f}, {hi:.3f}] {r['p80']:6.3f} {r['p90']:6.3f}"
                  + (f"  (t = {t:.3f})" if rule == "gate" else ""))
            if rule != "net" and (best is None or a > best["auc"]):
                best = r
        print(f"{name}: verifier on tuning balls median {np.median(v[y]):.2f}, on no-ball peaks median {np.median(v[~y]):.2f}")
    # paired bootstrap: chosen rule minus the net alone
    vb = Verifier(); vb.load_state_dict(torch.load(best["path"], map_location="cpu", weights_only=True)); v = predict(vb, X).astype(np.float64)
    sc = rule_scores(best["rule"], s, v, best["t"])
    diff = [auc(sc[b][y[b]], sc[b][~y[b]]) - auc(s[b][y[b]], s[b][~y[b]]) for b in boot]
    best["auc_gain_ci"] = list(np.nanpercentile(diff, [2.5, 97.5])); best["auc_net"] = auc(s[y], s[~y])
    print(f"\nchoice: {best['model']} / {best['rule']}  AUC {best['auc']:.3f} vs net {best['auc_net']:.3f}, "
          f"gain 95% CI [{best['auc_gain_ci'][0]:+.3f}, {best['auc_gain_ci'][1]:+.3f}]")
    json.dump({"best": best, "rows": rows}, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()

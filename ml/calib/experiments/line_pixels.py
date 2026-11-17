"""Feasibility probe (2026-11-18): can handball-line pixels be told from the other lines?

Fitting the court of a frame to its line pixels (`frame_fit.py`) failed on the first frames: the
true court scores *lower* than wrong courts, because a multi-sport floor has lines everywhere and
the classical line mask finds only part of the handball lines. Before any search, the question is
whether the line evidence can prefer the true court at all.

Test: for each truth frame (clicked truth, `ml/calib/truth_dev.json`) the true court is scored
against perturbed courts (the true court shifted by 1, 2 and 4 m along x and y, mirrored along x,
turned by 3 degrees about the camera); score = share of the court's line samples in the frame that
lie within 3 px of a line pixel. Masks compared:
- classic: `clicks.line_mask_png` (local top-hat / black-hat, any colour);
- learned: a pixel classifier (gradient boosting on 17 local features: Lab, top-hat and black-hat
  at three scales, ridge strength at two scales, gradient) trained on the handball-line pixels of
  the truth frames of the *other* pieces (5 folds grouped by piece), threshold 0.5.
Reported: share of frames where the true court beats every perturbed one, and the median margin.

    <venv with scikit-learn>/python ml/calib/experiments/line_pixels.py CACHE OUT_JSON
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import clicks  # noqa: E402

FINE = np.vstack([clicks.dense(c, 0.05) for c in clicks.CURVES.values()])
SCORE_PTS = np.vstack([v[:: max(1, len(v) // 160)] for v in clicks.DENSE.values()])


def features(img: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    lum = lab[:, :, 0]
    feats = [lab[:, :, 0], lab[:, :, 1], lab[:, :, 2]]
    for ks in (5, 9, 15):
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ks, ks))
        feats.append(cv2.morphologyEx(lum, cv2.MORPH_TOPHAT, k))
        feats.append(cv2.morphologyEx(lum, cv2.MORPH_BLACKHAT, k))
    k9 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    for c in (1, 2):
        feats.append(cv2.morphologyEx(lab[:, :, c], cv2.MORPH_TOPHAT, k9))
        feats.append(cv2.morphologyEx(lab[:, :, c], cv2.MORPH_BLACKHAT, k9))
    for s in (1.2, 2.5):
        g = cv2.GaussianBlur(lum, (0, 0), s)
        dxx = cv2.Sobel(g, cv2.CV_32F, 2, 0)
        dyy = cv2.Sobel(g, cv2.CV_32F, 0, 2)
        dxy = cv2.Sobel(g, cv2.CV_32F, 1, 1)
        tmp = np.sqrt((dxx - dyy) ** 2 + 4 * dxy**2)
        feats.append(np.maximum(np.abs(0.5 * (dxx + dyy + tmp)), np.abs(0.5 * (dxx + dyy - tmp))))
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1)
    feats.append(np.sqrt(gx**2 + gy**2))
    return np.stack(feats, -1)


def project(hh: np.ndarray, k: np.ndarray, size: tuple[int, int], pts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    q = np.c_[pts, np.ones(len(pts))] @ hh.T
    sign = np.sign(np.median((np.c_[[[20.0, 10.0]], [[1.0]]] @ hh.T)[:, 2])) or 1.0
    front = q[:, 2] * sign > 1e-9
    uv = np.full((len(pts), 2), -1e6)
    uv[front] = clicks.truth._distort(q[front, :2] / q[front, 2:3], k, size)
    return uv, front


def frame_label(img: np.ndarray, entry: dict) -> tuple[np.ndarray, np.ndarray]:
    """Handball-line pixels (3 px wide) and the region where the truth holds."""
    h, w = img.shape[:2]
    m = entry["model"]
    hh, k = np.array(m["h"]), np.array(m["k"])
    uv, front = project(hh, k, (w, h), FINE)
    lab = np.zeros((h, w), np.uint8)
    ok = front & (np.abs(uv) < 1e5).all(1)
    for p in uv[ok].astype(int):
        if 0 <= p[0] < w and 0 <= p[1] < h:
            cv2.circle(lab, (int(p[0]), int(p[1])), 1, 255, -1)
    region = np.zeros((h, w), np.uint8)
    g = np.array(entry["grid"]["px"], np.float32)
    if len(g) >= 3:
        cv2.fillConvexPoly(region, cv2.convexHull(g).astype(np.int32), 255)
        region = cv2.dilate(region, np.ones((61, 61), np.uint8))
    return lab > 0, region > 0


def court_score(dt: np.ndarray, hh: np.ndarray, k: np.ndarray, pts: np.ndarray) -> float:
    h, w = dt.shape
    uv, front = project(hh, k, (w, h), pts)
    ins = front & (uv[:, 0] >= 0) & (uv[:, 0] < w - 1) & (uv[:, 1] >= 0) & (uv[:, 1] < h - 1)
    if ins.sum() < 30:
        return 0.0
    return float((clicks.truth._sample(dt, uv[ins]) <= 3).mean())


def perturbed(hh: np.ndarray) -> list[np.ndarray]:
    out = []
    for d in (1.0, 2.0, 4.0):
        for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d)):
            out.append(hh @ np.array([[1, 0, -dx], [0, 1, -dy], [0, 0, 1.0]]))
    out.append(hh @ np.array([[-1, 0, 40], [0, 1, 0], [0, 0, 1.0]]))  # mirrored along x
    for a in (-3.0, 3.0):  # turned about the court centre
        c, s = np.cos(np.radians(a)), np.sin(np.radians(a))
        t = np.array([[1, 0, 20], [0, 1, 10], [0, 0, 1.0]]) @ np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]) @ np.array([[1, 0, -20], [0, 1, -10], [0, 0, 1.0]])
        out.append(hh @ t)
    return out


def main() -> None:
    from sklearn.ensemble import HistGradientBoostingClassifier

    cache, out = Path(sys.argv[1]), Path(sys.argv[2])
    truth = json.loads((HERE.parent / "truth_dev.json").read_text())
    frames = [(pid, fr, e) for pid, fs in sorted(truth.items()) for fr, e in fs.items() if e.get("model") and e.get("grid")]
    data = {}
    for pid, fr, e in frames:
        img = cv2.imread(str(cache / f"{pid}.frames" / f"{int(fr):05d}.jpg"))
        lab, region = frame_label(img, e)
        data[(pid, fr)] = (img, lab, region, e)
    pieces = sorted({pid for pid, _, _ in frames})
    rng = np.random.default_rng(0)
    folds = {p: i % 5 for i, p in enumerate(rng.permutation(pieces))}
    rows = []
    for fold in range(5):
        xs, ys = [], []
        for (pid, fr), (img, lab, region, _) in data.items():
            if folds[pid] == fold:
                continue
            f = features(img)
            pos = np.argwhere(lab & region)
            neg = np.argwhere(~lab & region)
            if len(pos) == 0:
                continue
            neg = neg[rng.choice(len(neg), min(len(neg), 4 * len(pos)), replace=False)]
            sel = np.vstack([pos, neg])
            xs.append(f[sel[:, 0], sel[:, 1]])
            ys.append(np.r_[np.ones(len(pos)), np.zeros(len(neg))])
        clf = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, max_leaf_nodes=63)
        clf.fit(np.vstack(xs), np.concatenate(ys))
        for (pid, fr), (img, lab, region, e) in data.items():
            if folds[pid] != fold:
                continue
            h, w = img.shape[:2]
            f = features(img).reshape(-1, 17)
            prob = clf.predict_proba(f)[:, 1].reshape(h, w)
            learned = (prob > 0.5).astype(np.uint8) * 255
            classic = clicks.line_mask_png(img)
            hh, k = np.array(e["model"]["h"]), np.array(e["model"]["k"])
            row = {"id": pid, "frame": fr}
            for name, mask in (("classic", classic), ("learned", learned)):
                dt = cv2.distanceTransform(255 - mask, cv2.DIST_L2, 3)
                kk = np.zeros(2)
                true_s = court_score(dt, hh, k, SCORE_PTS)
                others = [court_score(dt, p, kk, SCORE_PTS) for p in perturbed(hh)]
                row[name] = {"true": round(true_s, 3), "best_other": round(max(others), 3),
                             "wins": bool(true_s > max(others))}
            # pixel quality inside the truth region
            reg = region
            tp = float((learned[reg] > 0)[lab[reg]].mean()) if lab[reg].any() else 0.0
            prec = float(lab[reg][learned[reg] > 0].mean()) if (learned[reg] > 0).any() else 0.0
            row["learned_recall"], row["learned_precision"] = round(tp, 3), round(prec, 3)
            rows.append(row)
            print(pid, fr, row, flush=True)
    summary = {}
    for name in ("classic", "learned"):
        wins = [r[name]["wins"] for r in rows]
        margin = [r[name]["true"] - r[name]["best_other"] for r in rows]
        summary[name] = {"frames": len(rows), "true_court_wins": int(sum(wins)),
                         "share": round(float(np.mean(wins)), 3), "median_margin": round(float(np.median(margin)), 3)}
    summary["learned_pixels"] = {"recall_median": float(np.median([r["learned_recall"] for r in rows])),
                                 "precision_median": float(np.median([r["learned_precision"] for r in rows]))}
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()

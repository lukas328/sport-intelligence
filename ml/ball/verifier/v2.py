"""Verifier v2 data: one crop format for training and evaluation, plus the human-labelled hard peaks.

The human-labelled crops (hard-negative review of round 7's confident peaks in unseen games) were
made on Kaggle as: frames scaled to 1280 wide, a 96 px region around the peak (black outside the
frame) per frame, enlarged 2x with bicubic resampling, the three frames side by side, JPEG
quality 85. `canon_frames` repeats exactly that for any three frames (test set 2 triplets) and
then applies the verifier's own preprocessing (area downscale back to 96 px, centre cut), so train
and test crops pass through the same resampling. `canon_store` puts the v1 training crops
(72 px, data.py) through the same 2x up / JPEG / down round trip.

    # human crops + game split (about 2/3 of the games train, 1/3 tuning; never test set 2)
    python ml/ball/verifier/v2.py human ITEMS_JSON LABELS_DIR CROP_DIR HUMAN.npz
    # v1 crops through the same round trip
    python ml/ball/verifier/v2.py canon-v1 CROPS.npz CROPS_CANON.npz
"""
import json, sys, zlib
from pathlib import Path

import cv2, numpy as np

R, Q, STORE = 48, 85, 72


def _jpeg(img):
    return cv2.imdecode(cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, Q])[1], cv2.IMREAD_COLOR)


def from_strip(strip_bgr, out=STORE):
    """192 x 576 BGR strip (three 2x crops side by side) -> out x out x 9 RGB at frame scale."""
    w = strip_bgr.shape[1] // 3; o = (2 * R - out) // 2; res = []
    for j in range(3):
        c = cv2.resize(strip_bgr[:, j * w:(j + 1) * w], (2 * R, 2 * R), interpolation=cv2.INTER_AREA)
        res.append(cv2.cvtColor(c[o:o + out, o:o + out], cv2.COLOR_BGR2RGB))
    return np.concatenate(res, 2)


def canon_frames(frames_bgr, px, py, out=STORE):
    """Three BGR frames at 1280 wide and a peak -> crop exactly as the human-labelled crops, then from_strip."""
    px, py = int(px), int(py); strip = []
    for im in frames_bgr:
        pad = cv2.copyMakeBorder(im, R, R, R, R, cv2.BORDER_CONSTANT, value=(0, 0, 0))
        strip.append(cv2.resize(pad[py:py + 2 * R, px:px + 2 * R], (4 * R, 4 * R), interpolation=cv2.INTER_CUBIC))
    return from_strip(_jpeg(np.concatenate(strip, 1)), out)


def canon_store(x):
    """S x S x 9 RGB crop (v1 data) -> same size after the 2x bicubic / JPEG 85 / area round trip."""
    s = x.shape[0]
    strip = np.concatenate([cv2.cvtColor(np.ascontiguousarray(x[:, :, 3 * j:3 * j + 3]), cv2.COLOR_RGB2BGR) for j in range(3)], 1)
    strip = _jpeg(cv2.resize(strip, (6 * s, 2 * s), interpolation=cv2.INTER_CUBIC))
    return np.concatenate([cv2.cvtColor(cv2.resize(strip[:, j * 2 * s:(j + 1) * 2 * s], (s, s), interpolation=cv2.INTER_AREA),
                                        cv2.COLOR_BGR2RGB) for j in range(3)], 2)


def split_games(counts, frac=1 / 3, tries=20000):
    """Tuning games: about frac of the games whose ball and no-ball counts are closest to frac of the totals.
    counts: {game: (balls, nones)}. Deterministic (seeded search)."""
    rng = np.random.default_rng(0); games = sorted(counts); n = round(len(games) * frac)
    tb = sum(c[0] for c in counts.values()) * frac; tn = sum(c[1] for c in counts.values()) * frac
    best = None
    for _ in range(tries):
        sel = rng.choice(len(games), n, replace=False)
        b = sum(counts[games[i]][0] for i in sel); m = sum(counts[games[i]][1] for i in sel)
        err = abs(b - tb) / tb + abs(m - tn) / tn
        if best is None or err < best[0]:
            best = (err, sorted(games[i] for i in sel))
    return set(best[1])


def stage_human(items_json, labels_dir, crop_dir, out):
    items = {i["id"]: i for i in json.load(open(items_json))}
    lab = {}
    for f in sorted(Path(labels_dir).glob("*.json")):
        d = json.load(open(f)); d = d.get("data", d)
        if d.get("state") in ("ball", "none") and f.stem in items:
            lab[f.stem] = d["state"]
    counts = {}
    for k, s in lab.items():
        g = items[k]["game"]; c = counts.get(g, (0, 0)); counts[g] = (c[0] + (s == "ball"), c[1] + (s == "none"))
    tune = split_games(counts)
    X, y, game, is_tune, score, ids = [], [], [], [], [], []
    for k, s in lab.items():
        X.append(from_strip(cv2.imread(str(Path(crop_dir) / f"{k}.jpg")))); y.append(s == "ball")
        game.append(items[k]["game"]); is_tune.append(items[k]["game"] in tune); score.append(items[k]["score"]); ids.append(k)
    y, is_tune = np.array(y), np.array(is_tune)
    print(f"train: {len(counts) - len(tune)} games, {int((y & ~is_tune).sum())} ball, {int((~y & ~is_tune).sum())} none")
    print(f"tune:  {len(tune)} games, {int((y & is_tune).sum())} ball, {int((~y & is_tune).sum())} none")
    print("tuning games:", sorted(tune))
    np.savez(out, X=np.stack(X), y=y, game=np.array(game), tune=is_tune, score=np.array(score), id=np.array(ids))


def stage_canon_v1(crops, out):
    d = np.load(crops); X = d["X"]; Y = np.empty_like(X)
    for i in range(len(X)):
        Y[i] = canon_store(X[i])
        if i % 10000 == 0:
            print(i, len(X), flush=True)
    np.savez(out, X=Y, **{k: d[k] for k in d.files if k != "X"})


if __name__ == "__main__":
    {"human": stage_human, "canon-v1": stage_canon_v1}[sys.argv[1]](*sys.argv[2:])

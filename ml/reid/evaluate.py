"""Same-team retrieval on a held-out clip: our model(s) vs any ONNX embedder (e.g. the MSMT one).

Query and gallery are crops (or 10-second window means) of the same clip and team from different
10-second windows; a gallery item is right when it is the same identity (shirt number).
Metrics: rank-1 and mAP, over all queries with at least one right gallery item.

    python ml/reid/evaluate.py --data <dataset> --clip <clip> \
        --model fold.pt --onnx data/models/reid_bot_r50_msmt.onnx --cache <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import build_model, clean, load_index  # noqa: E402

WINDOW_S = 10.0


def eval_rows(data: Path, clip: str, every: int) -> list[dict]:
    rows = [r for r in clean(load_index(data), data, verbose=False) if r["clip"] == clip and r.get("numbered", True)]
    return [r for r in rows if (r["frame"] // 3) % every == 0]


def load_crops(data: Path, rows: list[dict]) -> np.ndarray:
    """N x 3 x 256 x 128 float32 RGB 0..255 (the Embedder interface)."""
    x = np.stack([cv2.imread(str(data / r["file"]))[:, :, ::-1] for r in rows])
    return np.ascontiguousarray(x.transpose(0, 3, 1, 2)).astype(np.float32)


def embed_onnx(path: Path, x: np.ndarray, threads: int, bs: int = 16) -> np.ndarray:
    import onnxruntime as ort

    o = ort.SessionOptions()
    o.intra_op_num_threads = threads
    s = ort.InferenceSession(str(path), o, providers=["CPUExecutionProvider"])
    name = s.get_inputs()[0].name
    return np.concatenate([s.run(None, {name: x[i : i + bs]})[0] for i in range(0, len(x), bs)])


def embed_torch(path: Path, x: np.ndarray, threads: int, bs: int = 64) -> np.ndarray:
    import torch

    torch.set_num_threads(threads)
    ck = torch.load(path, map_location="cpu", weights_only=True)
    m = build_model(size=tuple(ck["size"]), pretrained=False)
    m.load_state_dict(ck["state"])
    m.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(x), bs):
            xb = torch.from_numpy(x[i : i + bs])
            v = m(xb) + m(torch.flip(xb, dims=[3]))  # flip test-time augmentation
            out.append(torch.nn.functional.normalize(v, dim=1).numpy())
    return np.concatenate(out)


def retrieval(vecs: np.ndarray, ids: list[str], teams: list[str], wins: list[int]) -> dict:
    v = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
    sim = v @ v.T
    ids_a, teams_a, wins_a = np.array(ids), np.array(teams), np.array(wins)
    r1, aps = [], []
    for q in range(len(v)):
        g = (teams_a == teams_a[q]) & (wins_a != wins_a[q])
        if not g.any():
            continue
        right = ids_a[g] == ids_a[q]
        if not right.any() or right.all():
            continue
        order = np.argsort(-sim[q, g])
        hit = right[order]
        r1.append(float(hit[0]))
        prec = np.cumsum(hit) / np.arange(1, len(hit) + 1)
        aps.append(float((prec * hit).sum() / hit.sum()))
    return {"rank1": float(np.mean(r1)), "mAP": float(np.mean(aps)), "queries": len(r1)}


def evaluate(vecs: np.ndarray, rows: list[dict]) -> dict:
    ids = [r["identity"] for r in rows]
    teams = [r["team"] for r in rows]
    wins = [int(r["t"] // WINDOW_S) for r in rows]
    crop = retrieval(vecs, ids, teams, wins)
    groups: dict[tuple[str, int], list[int]] = defaultdict(list)
    for n, (i, w) in enumerate(zip(ids, wins, strict=True)):
        groups[(i, w)].append(n)
    keys = sorted(groups)
    mv = np.stack([vecs[groups[k]].mean(axis=0) for k in keys])
    win = retrieval(
        mv, [k[0] for k in keys], [k[0].split("/")[1] for k in keys], [k[1] for k in keys]
    )
    return {"crop": crop, "window": win}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--clip", required=True)
    ap.add_argument("--model", type=Path, nargs="*", default=[])
    ap.add_argument("--onnx", type=Path, nargs="*", default=[])
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--every", type=int, default=4, help="every n-th detected frame")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    rows = eval_rows(a.data, a.clip, a.every)
    n_id = len({r["identity"] for r in rows})
    print(f"{a.clip}: {len(rows)} eval crops, {n_id} identities", flush=True)
    x = None
    results = {}
    a.cache.mkdir(parents=True, exist_ok=True)
    for path in [*a.onnx, *a.model]:
        cp = a.cache / f"{path.stem}-{a.clip}-e{a.every}.npy"
        if cp.exists() and path.suffix == ".onnx":
            vecs = np.load(cp)
        else:
            if x is None:
                x = load_crops(a.data, rows)
            t = time.time()
            if path.suffix == ".onnx":
                vecs = embed_onnx(path, x, a.threads)
            else:
                vecs = embed_torch(path, x, a.threads)
            print(f"  {path.name}: {1000 * (time.time() - t) / len(x):.1f} ms/crop", flush=True)
            np.save(cp, vecs)
        res = evaluate(vecs, rows)
        results[path.name] = res
        c, w = res["crop"], res["window"]
        print(
            f"  {path.name:32s} crop rank1 {c['rank1']:.3f} mAP {c['mAP']:.3f} (q {c['queries']})"
            f" | window rank1 {w['rank1']:.3f} mAP {w['mAP']:.3f} (q {w['queries']})",
            flush=True,
        )
    if a.json:
        json.dump({"clip": a.clip, "crops": len(rows), "identities": n_id, **results},
                  open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()

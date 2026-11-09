"""Hidden-number test of ADR 027 with any embedder: numbered tracks (number voted from readings,
no appearance involved) are cut into 15-second pieces; each piece in turn loses its number and
reid.assign must find it among the other pieces. Reports found (assigned) and right.

Run with the project environment (handball_vision):

    uv run python ml/reid/hidden_numbers.py <clip> --obs <obs with numbers.npz> --cal-dir <dir> \
        --onnx model.onnx [--stored]  (--stored: use the embeddings stored in the observations)
"""

from __future__ import annotations

import argparse
import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from handball_vision import observe as ob
from handball_vision import reid
from handball_vision.calibration import Calibration
from handball_vision.motion import CameraMotion
from handball_vision.pipeline import iter_frames

ROOT = Path(__file__).resolve().parents[2]
VIEWS = ROOT / "data/views"
EVERY = 30  # video frames between embeddings (about one per second, as observe() does)
PIECE_S = 15.0


def bgr(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16))


def rosters_for(vid: str) -> dict[str, set[int]] | None:
    p = ROOT / "ml/eval/official" / f"{vid}.json"
    if not p.exists():
        return None
    out: dict[str, set[int]] = {"home": set(), "away": set()}
    for pl in json.load(open(p))["players"]:
        if str(pl.get("dressNr", "")).isdigit():
            out["home" if pl.get("isHome") else "away"].add(int(pl["dressNr"]))
    return out


def embeddings(vid: str, obs, model: Path, cache: Path) -> dict[tuple[int, int], np.ndarray]:
    if cache.exists():
        z = np.load(cache)
        return {(int(f), int(k)): v for (f, k), v in zip(z["idx"], z["vecs"], strict=True)}
    e = reid.Embedder(model, threads=4)
    by = {fo.index: fo for fo in obs.frames}
    out: dict[tuple[int, int], np.ndarray] = {}
    for n, frame in enumerate(iter_frames(ROOT / f"data/videos/{vid}.mp4")):
        if n % EVERY == 0 and n in by:
            vs = e.embed(frame, [(d.x1, d.y1, d.x2, d.y2) for d in by[n].people])
            out.update({(n, k): v for k, v in enumerate(vs) if v is not None})
    np.savez(cache, idx=np.array(list(out), np.int64).reshape(-1, 2), vecs=np.stack(list(out.values())))
    return out


def run(frags_numbered: list[reid.Fragment], fps: float) -> tuple[int, int, int, Counter]:
    ok = bad = unknown = 0
    conf: Counter = Counter()
    for k, c in enumerate(frags_numbered):
        test = reid.Fragment(
            c.track_id, c.team, c.first, c.last, c.start_xy, c.end_xy, c.vectors, None
        )
        pool = [x for j, x in enumerate(frags_numbered) if j != k] + [test]
        got = reid.assign(pool, fps).get(c.track_id)
        if got is None:
            unknown += 1
        elif got == c.number:
            ok += 1
        else:
            bad += 1
            conf[(c.number, got)] += 1
    return ok, bad, unknown, conf


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--obs", type=Path)
    ap.add_argument("--cal-dir", type=Path, required=True)
    ap.add_argument("--onnx", type=Path)
    ap.add_argument("--stored", action="store_true")
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    vid = a.clip
    motion = CameraMotion.load(VIEWS / f"{vid}-motion2.npz")
    obs = ob.load_observations(a.obs or VIEWS / f"{vid}-obs.npz", motion)
    stored = {(fo.index, k): v for fo in obs.frames for k, v in fo.embeds.items()}
    for fo in obs.frames:
        fo.embeds = {}
    a.cache.mkdir(parents=True, exist_ok=True)
    tp = a.cache / f"{vid}-track.pkl"
    if tp.exists():
        res = pickle.load(open(tp, "rb"))
    else:
        cal = Calibration.from_dict(pickle.load(open(a.cal_dir / f"{vid}-cal.pkl", "rb")))
        man = json.load(open(ROOT / "ml/eval/golden_set/manifest.json"))
        entry = next(m for m in man["matches"] if m["id"] == vid)
        kits = {k: bgr(v) for k, v in entry["kits"].items()}
        kits.setdefault("referee", (30, 30, 30))
        res = ob.track(obs, cal, kits, motion.background(), rosters=rosters_for(vid))
        pickle.dump(res, open(tp, "wb"))
    if a.stored:
        name, emb = "stored", stored
    else:
        assert a.onnx is not None
        name = a.onnx.stem
        emb = embeddings(vid, obs, a.onnx, a.cache / f"{vid}-{name}-emb.npz")
    fps = obs.fps
    rows: dict[int, list[tuple[int, np.ndarray, float, float]]] = defaultdict(list)
    for p in res.points:
        if p.det_index is not None and (p.frame, p.det_index) in emb:
            rows[p.track_id].append((p.frame, emb[(p.frame, p.det_index)], p.x, p.y))
    pieces: list[reid.Fragment] = []
    cid = 100000
    for tid, v in res.teams.items():
        if v.get("number") is None or str(v["label"]) == "referee" or tid not in rows:
            continue
        if int(v.get("number_readings", 0)) < 4:  # well-read numbers only (pipeline anchors)
            continue
        rs = sorted(rows[tid], key=lambda r: r[0])
        cur: list = []
        for r in [*rs, None]:
            if cur and (r is None or r[0] - cur[0][0] > PIECE_S * fps):
                pieces.append(
                    reid.Fragment(
                        cid,
                        str(v["label"]),
                        cur[0][0],
                        cur[-1][0],
                        (cur[0][2], cur[0][3]),
                        (cur[-1][2], cur[-1][3]),
                        np.stack([c[1] for c in cur]),
                        int(v["number"]),
                    )
                )
                cid += 1
                cur = []
            if r is not None:
                cur.append(r)
    players = {(f.team.removesuffix("_gk"), f.number) for f in pieces}
    print(f"{vid} [{name}] {len(players)} numbered players, {len(pieces)} pieces", flush=True)
    out = {"clip": vid, "model": name, "players": len(players), "pieces": len(pieces)}
    keep = (reid.MIN_ANCHOR_CONSISTENCY, reid.MIN_CANDIDATE_CONSISTENCY, reid.fit_projection)
    variants = {
        "default": keep,
        "no consistency gate": (-1.0, -1.0, keep[2]),
        "no projection, no gate": (-1.0, -1.0, lambda by, **kw: (lambda v: np.atleast_2d(v))),
    }
    for vname, (anc, cand, proj) in variants.items():
        reid.MIN_ANCHOR_CONSISTENCY, reid.MIN_CANDIDATE_CONSISTENCY = anc, cand
        reid.fit_projection = proj  # type: ignore[assignment]
        ok, bad, unk, conf = run(pieces, fps)
        n = max(1, len(pieces))
        print(
            f"  {vname:24s} found {(ok + bad) / n:.2f}  right of found {ok / max(1, ok + bad):.2f}"
            f"  right of all {ok / n:.2f}   (ok {ok} wrong {bad} unknown {unk})"
            f"  confusions {conf.most_common(4)}",
            flush=True,
        )
        out[vname] = {"ok": ok, "wrong": bad, "unknown": unk}
    reid.MIN_ANCHOR_CONSISTENCY, reid.MIN_CANDIDATE_CONSISTENCY, reid.fit_projection = keep
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()

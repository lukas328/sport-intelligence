"""Identity dataset for player re-identification, labelled by shirt numbers (no hand labelling).

Per clip: track() from stored observations (with shirt-number readings), keep tracks whose voted
number was read (not assigned by appearance), identity = clip/team/number (tracks with the same
identity are one player), crop the person box every `--every`-th detected frame (>= 64 px tall),
resize to 128 x 256 and write JPEGs plus an index JSON.

Run with the project environment (needs handball_vision):

    uv run python ml/reid/build_dataset.py --out <dir> \
        --obs ch-nlb-2017-horgen-moehlin=<obs-with-numbers.npz> ...
"""

from __future__ import annotations

import argparse
import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import cv2

from handball_vision import observe as ob
from handball_vision.calibration import Calibration
from handball_vision.motion import CameraMotion
from handball_vision.pipeline import iter_frames

ROOT = Path(__file__).resolve().parents[2]
VIEWS = ROOT / "data/views"
VIDEOS = ROOT / "data/videos"
CLIPS = ["ch-nlb-2017-horgen-moehlin", "ch-nlb-2017-horgen-staefa", "ch-spl2-2024-leimental-arbon"]
MIN_HEIGHT = 64
MIN_READ_CONF = 0.85


def bgr(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16))


def rosters_for(vid: str) -> dict[str, set[int]] | None:
    p = ROOT / "ml/eval/official" / f"{vid}.json"
    if not p.exists():
        return None
    players = json.load(open(p))["players"]
    out: dict[str, set[int]] = {"home": set(), "away": set()}
    for pl in players:
        if str(pl.get("dressNr", "")).isdigit():
            out["home" if pl.get("isHome") else "away"].add(int(pl["dressNr"]))
    return out


def covered(a: ob.Detection, others: list, k: int) -> float:
    """Largest fraction of box a covered by another person's box."""
    area = max(1.0, (a.x2 - a.x1) * (a.y2 - a.y1))
    best = 0.0
    for j, b in enumerate(others):
        if j == k:
            continue
        w = min(a.x2, b.x2) - max(a.x1, b.x1)
        h = min(a.y2, b.y2) - max(a.y1, b.y1)
        if w > 0 and h > 0:
            best = max(best, w * h / area)
    return best


def build(
    vid: str,
    obs_path: Path,
    cal_path: Path,
    out: Path,
    every: int,
    tracklets: bool,
    anchor_s: float = 0.0,
) -> list[dict]:
    motion = CameraMotion.load(VIEWS / f"{vid}-motion2.npz")
    obs = ob.load_observations(obs_path, motion)
    for fo in obs.frames:  # labels must not depend on the MSMT embedder
        fo.embeds = {}
    cal = Calibration.from_dict(pickle.load(open(cal_path, "rb")))
    man = json.load(open(ROOT / "ml/eval/golden_set/manifest.json"))
    entry = next(m for m in man["matches"] if m["id"] == vid)
    kits = {k: bgr(v) for k, v in entry["kits"].items()}
    kits.setdefault("referee", (30, 30, 30))
    rosters = rosters_for(vid)
    res = ob.track(obs, cal, kits, motion.background(), rosters=rosters)
    ident: dict[int, str] = {}
    for tid, v in res.teams.items():
        label = str(v.get("label", ""))
        if v.get("number") is None or v.get("number_source") == "appearance":
            continue
        if label.startswith("referee"):
            continue
        ident[tid] = f"{vid}/{label.removesuffix('_gk')}/{int(v['number'])}"
    span: dict[int, list[int]] = {}
    for p in res.points:  # observed span (a lost track coasts on for a while)
        if p.det_index is None:
            continue
        s = span.setdefault(p.track_id, [p.frame, p.frame])
        s[0], s[1] = min(s[0], p.frame), max(s[1], p.frame)
    by = {fo.index: fo for fo in obs.frames}
    step = int(res.extra.get("detect_every") or 3)
    point_id: dict[tuple[int, int], str] = {}  # (track, frame) -> identity (anchor mode)
    anchor_of: dict[tuple[int, int], int] = {}
    if anchor_s > 0:
        # labels from the readings themselves: a crop is labelled with a confident reading of its
        # own track at most anchor_s away (tracks swap people; a short window rarely does)
        ident = {}
        reads: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for p in res.points:
            if p.det_index is None or p.frame not in by:
                continue
            nc = by[p.frame].numbers.get(p.det_index)
            if nc is not None and nc[1] >= MIN_READ_CONF:
                reads[p.track_id].append((p.frame, int(nc[0])))
        for p in res.points:
            if p.track_id not in reads or p.det_index is None or (p.frame // step) % every:
                continue
            label = str(res.teams.get(p.track_id, {}).get("label", ""))
            if label.startswith("referee"):
                continue
            f, num = min(reads[p.track_id], key=lambda r: abs(r[0] - p.frame))
            if abs(f - p.frame) <= anchor_s * obs.fps:
                point_id[(p.track_id, p.frame)] = f"{vid}/{label.removesuffix('_gk')}/{num}"
                anchor_of[(p.track_id, p.frame)] = f
        numbered = set(reads)
    else:
        numbered = set(ident)
    if tracklets:  # unnumbered team tracks of 5 s or more: their own (pseudo) identity
        for tid, v in res.teams.items():
            label = str(v.get("label", ""))
            if tid in ident or tid in numbered or label not in ("home", "away", "home_gk", "away_gk"):
                continue
            if tid in span and span[tid][1] - span[tid][0] >= 5 * obs.fps:
                ident[tid] = f"{vid}/{label.removesuffix('_gk')}/t{tid}"
    want: dict[int, list[tuple[str, int, int]]] = defaultdict(list)  # frame -> (id, track, det)
    for p in res.points:
        if p.det_index is None or p.frame not in by or (p.frame // step) % every:
            continue
        i = point_id.get((p.track_id, p.frame)) or ident.get(p.track_id)
        if i is not None:
            want[p.frame].append((i, p.track_id, p.det_index))
    rows: list[dict] = []
    clash = 0
    for n, frame in enumerate(iter_frames(VIDEOS / f"{vid}.mp4")):
        if n not in want:
            continue
        ids = Counter(i for i, _, _ in want[n])
        people = by[n].people
        for i, tid, k in want[n]:
            if ids[i] > 1:  # two tracks claim the same player at once: unsure, drop
                clash += 1
                continue
            d = people[k]
            if d.y2 - d.y1 < MIN_HEIGHT:
                continue
            y1, y2 = max(0, round(d.y1)), min(frame.shape[0], round(d.y2))
            x1, x2 = max(0, round(d.x1)), min(frame.shape[1], round(d.x2))
            if y2 - y1 < MIN_HEIGHT or x2 - x1 < 8:
                continue
            crop = cv2.resize(frame[y1:y2, x1:x2], (128, 256), interpolation=cv2.INTER_LINEAR)
            rel = Path(vid) / i.split("/", 1)[1].replace("/", "_") / f"{n:05d}_{tid}.jpg"
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(out / rel), crop, [cv2.IMWRITE_JPEG_QUALITY, 93])
            team, number = i.split("/")[1:]
            is_num = not number.startswith("t")
            rows.append(
                {
                    "file": str(rel),
                    "clip": vid,
                    "team": team,
                    "number": int(number) if is_num else None,
                    "numbered": is_num,
                    "span": span[tid],
                    "anchor": anchor_of.get((tid, n)),
                    "identity": i,
                    "track": tid,
                    "frame": n,
                    "t": round(n / obs.fps, 2),
                    "box": [round(d.x1, 1), round(d.y1, 1), round(d.x2, 1), round(d.y2, 1)],
                    "height": round(d.y2 - d.y1, 1),
                    "covered": round(covered(d, people, k), 3),
                }
            )
    per = Counter(r["identity"] for r in rows if r["numbered"])
    n_tl = len({r["identity"] for r in rows if not r["numbered"]})
    print(
        vid,
        "identities",
        len(per),
        "crops",
        sum(per.values()),
        "tracklets",
        n_tl,
        "crops",
        len(rows) - sum(per.values()),
        "clashes dropped",
        clash,
        "tracks",
        len(ident),
        "of",
        len(res.teams),
        flush=True,
    )
    for i, c in sorted(per.items()):
        print("  ", i, c)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cal-dir", type=Path, required=True, help="<clip>-cal.pkl calibrations")
    ap.add_argument("--obs", nargs="*", default=[], help="clip=obs.npz overrides")
    ap.add_argument("--every", type=int, default=5, help="every n-th detected frame")
    ap.add_argument("--clips", nargs="*", default=CLIPS)
    ap.add_argument("--tracklets", action="store_true", help="also unnumbered team tracks")
    ap.add_argument(
        "--anchor", type=float, default=0.0, help="label crops from readings within this many s"
    )
    a = ap.parse_args()
    over = dict(s.split("=", 1) for s in a.obs)
    rows: list[dict] = []
    for vid in a.clips:
        obs_path = Path(over.get(vid, VIEWS / f"{vid}-obs.npz"))
        rows += build(vid, obs_path, a.cal_dir / f"{vid}-cal.pkl", a.out, a.every, a.tracklets, a.anchor)
    a.out.mkdir(parents=True, exist_ok=True)
    json.dump({"crops": rows}, open(a.out / "index.json", "w"))
    num = [r for r in rows if r["numbered"]]
    print("total numbered crops", len(num), "identities", len({r["identity"] for r in num}))
    print("tracklet crops", len(rows) - len(num))


if __name__ == "__main__":
    main()

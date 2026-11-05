"""Round 5 of the 3-frame ball net: OWLv2 pseudo-labels, temporally confirmed, added to the round 3 data mix.

1. Confirm: OWLv2 boxes (kernel handball-ball-owl: bursts of 5 frames, stride round(fps/25), every 6 s, boxes
   [cx, cy, w, h, score, query] in 1280-wide coordinates) are deduplicated (overlapping OWL tiles), linked inside
   each burst at a physically possible speed (balltrack.link), and kept when at least 3 of the 5 frames link with
   score >= CONF, the best box scores >= PEAK, and the chain moves: in the frame, against the camera and against
   its own surroundings (a spot glued to the background or a screen overlay is a fixed thing). Places where boxes come back in many
   bursts of a segment are fixed spots: those never become positives; the most persistent ones that do not move
   become hard negatives (only those: "OWL sees nothing" frames are not safe negatives).
2. Cut triplets (t-G, t, t+G; G = 3 above 40 fps, else 2, like collect_game/mine_gpu) of 224 px around the
   confirmed balls from the segment videos (frames scaled to 1280 wide like the bench).
3. Train from ball_best.pt (round 3) with the round 3 data mix plus the OWL tiles; Roboflow still frames down-
   weighted (round 4 showed they hurt). Tiles are preloaded into RAM (random reads from /kaggle/input are slow);
   the run stops inside the time budget (the cosine schedule is shortened if the measured speed needs it).
Outputs (small): ball_r5.pt, r5_stats.json, r5_review_pos.jpg, r5_review_neg.jpg; owl_tiles.zip (tiles + meta,
for reuse as a kernel source, not for download)."""
import glob, json, math, os, random, sys, time, zipfile, zlib
from collections import defaultdict
from dataclasses import dataclass, field
from multiprocessing import Pool
import cv2, numpy as np

T_START = time.time()
INP = os.environ.get("R5_INPUT", "/kaggle/input")
WORK = os.environ.get("R5_WORK", "/kaggle/working")
TMP = os.environ.get("R5_TMP", "/tmp/r5")
BUDGET_S = float(os.environ.get("R5_BUDGET_H", "8.5")) * 3600  # whole kernel, Kaggle GPU sessions stop at 9 h (12 h on some)
SMOKE = bool(os.environ.get("R5_SMOKE"))  # local test: CPU, few iterations, metas filtered to tiles that exist
os.makedirs(WORK, exist_ok=True); os.makedirs(f"{TMP}/owl/img", exist_ok=True)
def log(*a): print(f"[{time.time() - T_START:6.0f}s]", *a, flush=True)

# ------------------------------------------------------------------ 1. confirmation
CFG = dict(
    LINK=0.25,      # boxes from this score take part in linking
    CONF=0.35,      # a chain needs MIN_FRAMES boxes at least this confident
    PEAK=0.45,      # and its best box at least this (bench: 10 of 11 boxes >= 0.5 are the ball; hands/knees 0.35-0.45)
    MIN_FRAMES=3,   # of the 5 burst frames
    MIN_SIDE=5.0, MAX_SIDE=40.0,  # mean box side in 1280-wide px
    RADIUS=8.0,     # px, linking tolerance
    MAX_SPEED=1152.0,  # px/s at 1280 wide (0.9 frame widths per second, as in mine_gpu)
    SIZE_RATIO=2.2,
    MOVE_FRAME=2.0,  # px the chain must move in the frame (a screen overlay never does)
    MOVE_REL=1.5,    # px against the camera shift (block-median phase correlation), and ...
    MOVE_LOCAL=0.2,  # ... local motion against its own surroundings (mine_gpu). On 41 real chains every clear ball
                     # had >= 0.2, every head/fist/floor-logo false chain < 0.17
    CELL=16.0,       # px, grid for fixed spots across bursts
    STATIC_SHARE=0.15, STATIC_MIN=4,   # a cell with boxes in this share of bursts: never a positive
    HARD_SHARE=0.25, HARD_MIN=5,       # stricter: hard-negative source
    HARD_SCORE=0.2, HARD_STILL=1.5,    # box score, max movement in the burst (px)
    POS_PER_CHAIN=3, NEG_PER_CELL=6, NEG_PER_SEG=40,
    TILE=224, MARGIN=40,
)
CFG.update({k: type(v)(os.environ[f"R5_{k}"]) for k, v in CFG.items() if f"R5_{k}" in os.environ})


@dataclass(frozen=True)
class Peak:
    frame: int
    x: float
    y: float
    score: float
    w: float = 0.0
    q: int = 0


@dataclass
class Tracklet:
    peaks: list = field(default_factory=list)
    vx: float = 0.0
    vy: float = 0.0


def link(peaks, fps, max_speed, radius, max_gap=3):
    """balltrack.link (packages/vision/handball_vision/balltrack.py): each peak joins the open tracklet whose
    constant-velocity prediction is nearest, within a physically possible step; stronger peaks first."""
    by_frame = defaultdict(list)
    for p in peaks:
        by_frame[p.frame].append(p)
    done, open_ = [], []
    for f in sorted(by_frame):
        still = []
        for t in open_:
            (done if f - t.peaks[-1].frame > max_gap else still).append(t)
        open_ = still; taken = set()
        for p in sorted(by_frame[f], key=lambda q: -q.score):
            best, best_d = None, math.inf
            for k, t in enumerate(open_):
                if k in taken:
                    continue
                last = t.peaks[-1]; dt = (f - last.frame) / fps
                if math.hypot(p.x - last.x, p.y - last.y) > radius + max_speed * dt:
                    continue
                d = math.hypot(p.x - (last.x + t.vx * dt), p.y - (last.y + t.vy * dt))
                if d <= radius + 0.5 * max_speed * dt and d < best_d:
                    best, best_d = k, d
            if best is None:
                open_.append(Tracklet([p])); taken.add(len(open_) - 1); continue
            t = open_[best]; last = t.peaks[-1]; dt = (f - last.frame) / fps
            vx, vy = (p.x - last.x) / dt, (p.y - last.y) / dt; a = 0.5 if len(t.peaks) > 1 else 1.0
            t.vx, t.vy = (1 - a) * t.vx + a * vx, (1 - a) * t.vy + a * vy
            t.peaks.append(p); taken.add(best)
    return done + open_


def dedupe(boxes, c=CFG):
    """OWL tiles overlap: the same ball comes back from two tiles. Keep the strongest box per place."""
    out = []
    for b in sorted(boxes, key=lambda b: -b[4]):
        side = 0.5 * (b[2] + b[3])
        if not (c["MIN_SIDE"] <= side <= c["MAX_SIDE"]):
            continue
        if all(math.hypot(b[0] - o[0], b[1] - o[1]) > max(6.0, 0.6 * side) for o in out):
            out.append(b)
    return out


def fixed_cells(bursts, thr, share, least, c=CFG):
    """Grid cells where boxes >= thr come back in at least `share` of the bursts (and `least` bursts): fixed
    things. Like balltrack.static_cells: the 3x3 neighbourhood counts (a spot on a border), the cell itself half."""
    hit = defaultdict(set)
    for bi, b in enumerate(bursts):
        for fr in b["frames"]:
            for x in fr["boxes"]:
                if x[4] >= thr:
                    hit[(int(x[0] // c["CELL"]), int(x[1] // c["CELL"]))].add(bi)
    near = {}
    for k in hit:
        s = set()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                s |= hit.get((k[0] + dx, k[1] + dy), set())
        near[k] = s
    need = max(least, share * max(1, len(bursts)))
    return {k for k in hit if len(near[k]) >= need and len(hit[k]) >= need / 2}


def plan_segment(seg, c=CFG):
    """JSON-only part: candidate chains per burst, fixed spots, hard-negative spots. No video needed."""
    fps = float(seg["fps"]) or 25.0; stride = int(seg.get("stride") or max(1, round(fps / 25)))
    bursts = [b for b in seg["bursts"] if b.get("frames")]
    for b in bursts:
        for fr in b["frames"]:
            fr["boxes"] = dedupe(fr["boxes"], c)
    static = fixed_cells(bursts, c["LINK"], c["STATIC_SHARE"], c["STATIC_MIN"], c)
    hard = fixed_cells(bursts, c["HARD_SCORE"], c["HARD_SHARE"], c["HARD_MIN"], c)
    cellof = lambda x, y: (int(x // c["CELL"]), int(y // c["CELL"]))
    st = defaultdict(int); plans = []
    for bi, b in enumerate(bursts):
        frames = [fr["f"] for fr in b["frames"]]
        peaks = [Peak(fr["f"], x[0], x[1], x[4], 0.5 * (x[2] + x[3]), int(x[5])) for fr in b["frames"] for x in fr["boxes"] if x[4] >= c["LINK"]]
        trs = link(peaks, fps, c["MAX_SPEED"], c["RADIUS"], max_gap=2 * stride)
        st["bursts"] += 1; st["bursts_with_box_conf"] += any(p.score >= c["CONF"] for p in peaks)
        chains = []
        for t in trs:
            ps = t.peaks; n_conf = sum(p.score >= c["CONF"] for p in ps)
            if n_conf < c["MIN_FRAMES"]:
                continue
            st["chains_3of5"] += 1
            sides = [p.w for p in ps]; top = max(p.score for p in ps)
            for pk in (0.35, 0.4, 0.45, 0.5, 0.6):  # sensitivity of the PEAK rule (before size, fixed-spot and motion tests)
                st[f"chains_peak{pk}"] += top >= pk
            if top < c["PEAK"]:
                st["drop_peak"] += 1; continue
            if max(sides) > c["SIZE_RATIO"] * min(sides):
                st["drop_size"] += 1; continue
            if sum(cellof(p.x, p.y) in static for p in ps) * 2 >= len(ps):
                st["drop_static_cell"] += 1; continue
            chains.append(ps)
        # hard negatives: boxes in the persistent cells that do not move inside the burst
        negs = []
        for k in hard:
            pk = [Peak(fr["f"], x[0], x[1], x[4]) for fr in b["frames"] for x in fr["boxes"] if x[4] >= c["HARD_SCORE"] and cellof(x[0], x[1]) == k]
            if len({p.frame for p in pk}) < c["MIN_FRAMES"]:
                continue
            xs = [p.x for p in pk]; ys = [p.y for p in pk]
            if max(max(xs) - min(xs), max(ys) - min(ys)) > c["HARD_STILL"]:
                continue
            negs.append((k, float(np.median(xs)), float(np.median(ys))))
        others = [(fr["f"], x[0], x[1], x[4]) for fr in b["frames"] for x in fr["boxes"] if x[4] >= c["LINK"] and cellof(x[0], x[1]) not in static]
        if chains or negs:
            plans.append({"burst": bi, "frames": frames, "chains": chains, "negs": negs, "others": others})
    st["static_cells"] = len(static); st["hard_cells"] = len(hard)
    return fps, stride, plans, dict(st)


def local_motion(trip, cx, cy, r=64, q=8):
    """mine_gpu: how much the spot moves against its own surroundings (0: glued to the background)."""
    H, W = trip[0].shape[:2]; x0 = int(np.clip(cx - r, 0, W - 2 * r)); y0 = int(np.clip(cy - r, 0, H - 2 * r))
    g = [cv2.cvtColor(t[y0:y0 + 2 * r, x0:x0 + 2 * r], cv2.COLOR_BGR2GRAY).astype(np.float32) for t in trip]
    px, py = int(cx - x0), int(cy - y0); cc = g[1][max(0, py - q):py + q, max(0, px - q):px + q]
    if cc.size == 0:
        return 0.0
    contrast = float(cc.std()) + 4.0; out = []
    for o in (g[0], g[2]):
        (dx, dy), _ = cv2.phaseCorrelate(g[1], o)
        M = np.float32([[1, 0, -dx], [0, 1, -dy]]); al = cv2.warpAffine(o, M, (2 * r, 2 * r), borderMode=cv2.BORDER_REPLICATE)
        a = al[max(0, py - q):py + q, max(0, px - q):px + q]; out.append(float(np.abs(a - cc).mean()) / contrast)
    return min(out)


def cam_shift(a, b, nx=5, ny=4):
    """Camera shift between two frames: median of block-wise phase correlations (half scale), so a static
    screen overlay or a few running players do not decide it."""
    ga = cv2.cvtColor(cv2.resize(a, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
    gb = cv2.cvtColor(cv2.resize(b, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
    H, W = ga.shape; bh, bw = H // ny, W // nx; win = cv2.createHanningWindow((bw, bh), cv2.CV_32F); sh = []
    for j in range(ny):
        for i in range(nx):
            pa = ga[j * bh:(j + 1) * bh, i * bw:(i + 1) * bw]; pb = gb[j * bh:(j + 1) * bh, i * bw:(i + 1) * bw]
            if pa.std() < 3:  # flat block (floor, black bar): no information
                continue
            (dx, dy), r = cv2.phaseCorrelate(pa, pb, win)
            if r > 0.1:
                sh.append((dx, dy))
    if not sh:
        return 0.0, 0.0
    sh = np.array(sh); return 2 * float(np.median(sh[:, 0])), 2 * float(np.median(sh[:, 1]))


def tile_at(frames, ts, cx, cy, rng, c=CFG, centred=False):
    """224 px triplet around (cx, cy); the point lands at a random place at least MARGIN from the edges."""
    T = c["TILE"]; H, W = frames[ts[1]].shape[:2]
    if centred:
        u = v = T / 2
    else:
        u = rng.uniform(c["MARGIN"], T - c["MARGIN"]); v = rng.uniform(c["MARGIN"], T - c["MARGIN"])
    x0 = int(np.clip(round(cx - u), 0, W - T)); y0 = int(np.clip(round(cy - v), 0, H - T))
    return cv2.hconcat([frames[t][y0:y0 + T, x0:x0 + T] for t in ts]), x0, y0


def process_segment(args):
    """Plan from the JSON, then one sequential pass over the video (grab every frame: frame numbers match the
    OWL kernel's), cutting tiles burst by burst."""
    jpath, vpath, val = args
    seg = json.load(open(jpath)); c = CFG; name = os.path.basename(vpath)[:-4]
    game = name.rsplit("_s", 1)[0] if "_s" in name else name
    rng = random.Random(zlib.crc32(name.encode()))
    fps, stride, plans, st = plan_segment(seg, c)
    G = 3 if fps > 40 else 2
    need = {}
    for pl in plans:
        fs = set(pl["frames"])
        for ps in pl["chains"]:
            for p in ps:
                fs |= {p.frame - G, p.frame + G}
        for f in pl["frames"]:
            fs |= {f - G, f + G}
        for f in fs:
            need[f] = pl["burst"]
    by_burst = defaultdict(set)
    for f, b in need.items():
        by_burst[b].add(f)
    order = {pl["burst"]: pl for pl in plans}; last_of = {b: max(fs) for b, fs in by_burst.items()}
    meta, review = [], []; nneg_cell = defaultdict(int); st.update(confirmed=0, pos_tiles=0, neg_tiles=0, drop_still=0, drop_conflict=0)
    if not plans:
        return name, game, meta, st, review
    cap = cv2.VideoCapture(vpath); f = 0; buf = {}; todo = sorted(by_burst, key=lambda b: last_of[b]); ti = 0
    endf = max(last_of.values())
    while f <= endf and ti < len(todo):
        if not cap.grab():
            break
        if f in need:
            ok, im = cap.retrieve()
            if ok:
                if im.shape[1] != 1280:
                    im = cv2.resize(im, (1280, round(im.shape[0] * 1280 / im.shape[1])), interpolation=cv2.INTER_AREA)
                buf[f] = im
        while ti < len(todo) and f >= last_of[todo[ti]]:
            pl = order[todo[ti]]; ti += 1
            fr = {k: buf[k] for k in by_burst[pl["burst"]] if k in buf}
            cut_burst(pl, fr, G, name, game, val, rng, meta, review, st, nneg_cell)
            for k in by_burst[pl["burst"]]:
                buf.pop(k, None)
        f += 1
    cap.release()
    return name, game, meta, st, review


def cut_burst(pl, fr, G, name, game, val, rng, meta, review, st, nneg_cell, c=CFG):
    split = "val" if val else "train"; src = f"owl_{game}"
    moving = []
    for ps in pl["chains"]:
        a, b = ps[0], ps[-1]
        if a.frame not in fr or b.frame not in fr:
            continue
        mid = ps[len(ps) // 2]
        disp = math.hypot(b.x - a.x, b.y - a.y)
        dx, dy = cam_shift(fr[a.frame], fr[b.frame])
        rel = math.hypot(b.x - a.x - dx, b.y - a.y - dy)
        lm = local_motion((fr[a.frame], fr[mid.frame], fr[b.frame]), mid.x, mid.y) if mid.frame in fr else 0.0
        if disp < c["MOVE_FRAME"] or rel < c["MOVE_REL"] or lm < c["MOVE_LOCAL"]:
            st["drop_still"] += 1; continue
        moving.append((ps, round(disp, 1), round(rel, 1), round(lm, 3)))
    for ci, (ps, disp, rel, lm) in enumerate(moving):
        st["confirmed"] += 1
        others = [q for j, m in enumerate(moving) if j != ci for q in m[0]]
        cand = sorted(ps, key=lambda p: -p.score)[:c["POS_PER_CHAIN"]]
        for p in sorted(cand, key=lambda p: p.frame):
            ts = (p.frame - G, p.frame, p.frame + G)
            if any(t not in fr for t in ts):
                continue
            img, x0, y0 = tile_at(fr, ts, p.x, p.y, rng, c)
            T = c["TILE"]
            if any(q.frame == p.frame and x0 <= q.x < x0 + T and y0 <= q.y < y0 + T and math.hypot(q.x - p.x, q.y - p.y) > 12 for q in others):
                st["drop_conflict"] += 1; continue  # a second moving "ball" in the tile: the heatmap has one target
            fn = f"owl_{name}_{p.frame}_p{ci}.jpg"; cv2.imwrite(f"{TMP}/owl/img/{fn}", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
            meta.append({"file": fn, "split": split, "ball": [round(p.x - x0, 1), round(p.y - y0, 1), round(p.w, 1)], "src": src,
                         "tile": T, "root": f"{TMP}/owl", "score": round(p.score, 3), "q": p.q, "disp": disp, "rel": rel, "lm": lm})
            st["pos_tiles"] += 1
            review.append(("p", fn, p.x - x0, p.y - y0, p.score))
    if st["neg_tiles"] >= c["NEG_PER_SEG"]:
        return
    for k, x, y in pl["negs"]:
        if nneg_cell[k] >= c["NEG_PER_CELL"] or st["neg_tiles"] >= c["NEG_PER_SEG"]:
            continue
        f = pl["frames"][len(pl["frames"]) // 2]; ts = (f - G, f, f + G)
        if any(t not in fr for t in ts):
            continue
        img, x0, y0 = tile_at(fr, ts, x, y, rng, c)
        T = c["TILE"]
        # nothing else ball-like (outside fixed spots) anywhere in the tile in this burst: the real ball may hide there
        if any(x0 - 8 <= ox < x0 + T + 8 and y0 - 8 <= oy < y0 + T + 8 and math.hypot(ox - x, oy - y) > 12 for _, ox, oy, _ in pl["others"]):
            continue
        if any(x0 - 8 <= p.x < x0 + T + 8 and y0 - 8 <= p.y < y0 + T + 8 for ps in pl["chains"] for p in ps):
            continue
        fn = f"owl_{name}_{f}_n{k[0]}_{k[1]}.jpg"; cv2.imwrite(f"{TMP}/owl/img/{fn}", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        meta.append({"file": fn, "split": split, "ball": None, "src": src, "tile": T, "root": f"{TMP}/owl", "owl_static": [round(x - x0, 1), round(y - y0, 1)]})
        nneg_cell[k] += 1; st["neg_tiles"] += 1
        review.append(("n", fn, x - x0, y - y0, 0.0))


def review_sheet(items, path, n=48):
    tiles = []
    for kind, fn, bx, by, sc in items[:n]:
        t = cv2.imread(f"{TMP}/owl/img/{fn}")
        if t is None:
            continue
        w = t.shape[1] // 3; mid = t[:, w:2 * w]
        p = cv2.copyMakeBorder(mid, 48, 48, 48, 48, cv2.BORDER_CONSTANT); x, y = int(bx), int(by)
        crop = cv2.resize(p[y:y + 96, x:x + 96], (160, 160), interpolation=cv2.INTER_NEAREST)
        cv2.circle(crop, (80, 80), 22, (0, 255, 0) if kind == "p" else (0, 0, 255), 1)
        cv2.putText(crop, f"{sc:.2f} {fn[4:30]}", (2, 12), 0, 0.33, (255, 255, 255), 1); tiles.append(crop)
    if not tiles:
        return
    while len(tiles) % 8:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(path, cv2.vconcat([cv2.hconcat(tiles[i:i + 8]) for i in range(0, len(tiles), 8)]), [cv2.IMWRITE_JPEG_QUALITY, 85])


def build_owl():
    ALL = glob.glob(INP + "/**/*", recursive=True)
    vids = {os.path.basename(a)[:-4]: a for a in ALL if a.endswith(".mp4")}
    jsons = []
    for a in ALL:
        if a.endswith(".json") and os.path.basename(os.path.dirname(a)) == "segs":
            try:
                d = json.load(open(a))
            except Exception:
                continue
            if isinstance(d, dict) and "bursts" in d:
                v = vids.get(os.path.basename(d.get("file", ""))[:-4]) or vids.get(os.path.basename(a)[:-5])
                if v:
                    jsons.append((a, v))
                else:
                    log("no video for", a)
    if not jsons:  # output layout changed: any JSON with bursts
        for a in ALL:
            if a.endswith(".json") and os.path.getsize(a) < 50e6:
                try:
                    d = json.load(open(a))
                except Exception:
                    continue
                if isinstance(d, dict) and "bursts" in d and vids.get(os.path.basename(d.get("file", ""))[:-4]):
                    jsons.append((a, vids[os.path.basename(d["file"])[:-4]]))
    log(len(jsons), "OWL segment files,", len(vids), "videos")
    games = sorted({os.path.basename(v)[:-4].rsplit("_s", 1)[0] for _, v in jsons})
    val_games = {games[len(games) // 2]} if len(games) >= 6 else set()  # one game held out to watch the OWL group
    log("games", len(games), "val games", sorted(val_games))
    args = [(j, v, os.path.basename(v)[:-4].rsplit("_s", 1)[0] in val_games) for j, v in sorted(jsons)]
    meta, stats, review = [], {}, []
    with Pool(max(1, min(4, os.cpu_count() or 2))) as pool:
        for name, game, m, st, rv in pool.imap_unordered(process_segment, args):
            meta += m; stats[name] = st; review += rv
            log(name, {k: st.get(k, 0) for k in ("bursts", "chains_3of5", "confirmed", "pos_tiles", "neg_tiles", "drop_peak", "drop_static_cell", "drop_still")})
    per_game = defaultdict(lambda: defaultdict(int))
    for name, st in stats.items():
        g = name.rsplit("_s", 1)[0]; per_game[g]["segments"] += 1
        for k, v in st.items():
            per_game[g][k] += v
    tot = defaultdict(int)
    for g in per_game.values():
        for k, v in g.items():
            tot[k] += v
    json.dump(meta, open(f"{TMP}/owl/meta_owl.json", "w"))
    rng = random.Random(0); pos = [r for r in review if r[0] == "p"]; neg = [r for r in review if r[0] == "n"]
    rng.shuffle(pos); rng.shuffle(neg)
    review_sheet(pos, f"{WORK}/r5_review_pos.jpg", 64); review_sheet(neg, f"{WORK}/r5_review_neg.jpg", 32)
    out = {"cfg": CFG, "total": dict(tot), "per_game": {g: dict(v) for g, v in sorted(per_game.items())}, "val_games": sorted(val_games)}
    log("OWL confirmation total", dict(tot))
    return meta, out


owl_meta, R5 = build_owl()
json.dump(R5, open(f"{WORK}/r5_stats.json", "w"), indent=1)
if os.environ.get("R5_PREP_ONLY"):
    log("prep only: stop"); sys.exit(0)

# ------------------------------------------------------------------ 2. training (kaggle_train_fast + OWL groups)
import torch, torch.nn as nn, torch.nn.functional as F, torchvision
from pathlib import Path
from torch.utils.data import IterableDataset, DataLoader
_D = os.path.dirname(glob.glob(INP + "/**/meta_tt.json", recursive=True)[0])
_D2 = os.path.dirname(glob.glob(INP + "/**/meta_seq.json", recursive=True)[0])
_DS = glob.glob(INP + "/**/basketball-instants-dataset.json", recursive=True)
_RF = glob.glob(INP + "/**/meta_roboflow.json", recursive=True)
_METAS = "meta_tt.json,meta_ourlab.json,meta_lab3.json,meta_user.json,meta_konstanz_wuerzburg.json,meta_uznach_dietikon.json,meta_eisenach_wetzlar.json,meta_leimental_frauenfeld.json,meta_muelheim_suedpfalz.json,meta_u20_sui_ger.json"
ITERS = int(os.environ.get("ITERS", "20000"))
INIT = (glob.glob(INP + "/**/ball_best.pt", recursive=True) or [_D + "/ball3a.pt"])[0]
log("data", _D, _D2, _DS, _RF, "init", INIT)
torch.set_num_threads(4); random.seed(0); np.random.seed(0); torch.manual_seed(0)
D = Path(_D); T = 192
meta = [m for f in _METAS.split(",") if os.path.exists(D / f) for m in json.load(open(D / f))]
if SMOKE:
    meta = [m for m in meta if os.path.exists(Path(m.get("root", D)) / ("cand" if m["file"].startswith(("cand_", "mine_")) else "img") / m["file"])]
tr = [m for m in meta if m["split"] == "train"]; va = [m for m in meta if m["split"] != "train"]; random.shuffle(va); va = va[:2000]


class BallNet3(nn.Module):
    def __init__(s):
        super().__init__()
        r = torchvision.models.resnet18(weights=None)
        c1 = nn.Conv2d(9, 64, 7, 2, 3, bias=False)
        s.stem = nn.Sequential(c1, r.bn1, r.relu, r.maxpool); s.l1 = r.layer1; s.l2 = r.layer2
        s.up = nn.Sequential(nn.Conv2d(128, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU())
        s.head = nn.Sequential(nn.Conv2d(128, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.Conv2d(64, 1, 1))
        s.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406] * 3).view(1, 9, 1, 1) * 255); s.register_buffer("std", torch.tensor([0.229, 0.224, 0.225] * 3).view(1, 9, 1, 1) * 255)

    def forward(s, x):  # N,9,H,W RGB 0..255 (prev, centre, next) -> N,1,H/4,W/4 logits
        x = (x - s.mean) / s.std; a = s.l1(s.stem(x)); b = s.l2(a)
        b = F.interpolate(s.up(b), size=a.shape[-2:], mode="bilinear", align_corners=False)
        return s.head(torch.cat([a, b], 1))


def path_of(m):
    return Path(m.get("root", D)) / ("cand" if m["file"].startswith(("cand_", "mine_")) else "img") / m["file"]


def read(m):
    t = cv2.cvtColor(cv2.imread(str(path_of(m))), cv2.COLOR_BGR2RGB); w = t.shape[1] // 3
    return np.concatenate([t[:, 0:w], t[:, w:2 * w], t[:, 2 * w:3 * w]], 2)


def load_val(m):
    img = read(m); ball = list(m["ball"]) if m["ball"] else None
    if img.shape[0] > T or img.shape[1] > T:  # larger tiles: a fixed 192 window around the ball (or the centre)
        H, W = img.shape[:2]; cx, cy = (ball[0], ball[1]) if ball else (W / 2, H / 2)
        x0 = int(np.clip(cx - T / 2, 0, W - T)); y0 = int(np.clip(cy - T / 2, 0, H - T)); img = img[y0:y0 + T, x0:x0 + T]
        if ball:
            ball = [ball[0] - x0, ball[1] - y0, ball[2]]
    return img, ball


def focal(logit, gt):
    p = torch.sigmoid(logit).clamp(1e-4, 1 - 1e-4); pos = gt > 0.95
    pl = -torch.log(p) * (1 - p) ** 2 * pos; nl = -torch.log(1 - p) * p ** 2 * (1 - gt) ** 4 * (~pos)
    return (pl.sum() + nl.sum()) / max(1, int(pos.sum()))


# research-only extras: our labelled sequences, DeepSport basketball (CC BY-NC-SA)
_seq = json.load(open(_D2 + "/meta_seq.json"))
for m in _seq:
    m["root"] = _D2
if SMOKE:
    _seq = [m for m in _seq if os.path.exists(path_of(m))]


def project(cal, X):
    K = np.array(cal["KK"]).reshape(3, 3); R = np.array(cal["R"]).reshape(3, 3); Tt = np.array(cal["T"]); k1, k2, p1, p2, k3 = cal["kc"]
    Xc = R @ np.asarray(X) + Tt; x, y = Xc[0] / Xc[2], Xc[1] / Xc[2]; r2 = x * x + y * y; rad = 1 + k1 * r2 + k2 * r2 * r2 + k3 * r2 ** 3
    xd = x * rad + 2 * p1 * x * y + p2 * (r2 + 2 * x * x); yd = y * rad + p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
    u, v, _ = K @ np.array([xd, yd, 1.0]); return u, v, K[0, 0] * 12.0 / Xc[2]  # radius 12 cm -> px


def build_deepsport(root, out, Tt=320, seed=0):
    """DeepSport basketball instants -> triplet tiles (research only, CC BY-NC-SA); ball scaled to 8-24 px,
    neighbours are the +40 ms frame on both sides."""
    random.seed(seed); os.makedirs(out + "/img", exist_ok=True)
    ann = json.load(open(root + "/basketball-instants-dataset.json")); res = []
    for a in ann:
        for b in a.get("annotations", []):
            if b.get("type") != "ball" or not b.get("visible", True):
                continue
            cam = b.get("image", 0) + 1; base = f"{root}/{a['arena_label']}/{a['game_id']}/camcourt{cam}_{a['timestamp']}"
            if not (os.path.exists(base + ".json") and os.path.exists(base + "_0.png") and os.path.exists(base + "_40.png")):
                continue
            cal = json.load(open(base + ".json"))["calibration"]; u, v, r = project(cal, b["center"])
            i0 = cv2.imread(base + "_0.png"); i1 = cv2.imread(base + "_40.png")
            if i0 is None or i1 is None or not (0 <= u < i0.shape[1] and 0 <= v < i0.shape[0]) or r <= 1:
                continue
            s = random.uniform(8, 24) / (2 * r)
            if s < 1:
                i0 = cv2.resize(i0, None, fx=s, fy=s, interpolation=cv2.INTER_AREA); i1 = cv2.resize(i1, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            else:
                s = 1.0
            u, v = u * s, v * s; H, W = i0.shape[:2]
            if H < Tt or W < Tt:
                continue
            ims = [i1, i0, i1]; tag = f"ds_{a['arena_label']}_{a['timestamp']}_{cam}"
            for j in range(2):
                x0 = int(np.clip(u - random.uniform(30, Tt - 30), 0, W - Tt)); y0 = int(np.clip(v - random.uniform(30, Tt - 30), 0, H - Tt))
                fn = f"{tag}_p{j}.jpg"; cv2.imwrite(f"{out}/img/{fn}", cv2.hconcat([i[y0:y0 + Tt, x0:x0 + Tt] for i in ims]), [cv2.IMWRITE_JPEG_QUALITY, 92])
                res.append({"file": fn, "split": "train", "ball": [u - x0, v - y0, 2 * r * s], "src": "deepsport", "tile": Tt, "root": out})
            for j in range(2):
                for _ in range(20):
                    x0 = random.randint(0, W - Tt); y0 = random.randint(0, H - Tt)
                    if not (x0 - 20 < u < x0 + Tt + 20 and y0 - 20 < v < y0 + Tt + 20):
                        break
                else:
                    continue
                fn = f"{tag}_n{j}.jpg"; cv2.imwrite(f"{out}/img/{fn}", cv2.hconcat([i[y0:y0 + Tt, x0:x0 + Tt] for i in ims]), [cv2.IMWRITE_JPEG_QUALITY, 92])
                res.append({"file": fn, "split": "train", "ball": None, "src": "deepsport", "tile": Tt, "root": out})
    return res


_dsp = build_deepsport(os.path.dirname(_DS[0]), f"{TMP}/dsp") if _DS else []
_rf = json.load(open(_RF[0])) if _RF else []
for m in _rf:
    m["root"] = os.path.dirname(_RF[0])
log("seq", len(_seq), "deepsport", len(_dsp), "roboflow", len(_rf), "owl", len(owl_meta))
tr = tr + _seq + _dsp + [m for m in _rf if m["split"] == "train"] + [m for m in owl_meta if m["split"] == "train"]
_owl_va = [m for m in owl_meta if m["split"] != "train"]; random.shuffle(_owl_va)
if SMOKE:
    va = va[:200]
va = va + [m for m in _rf if m["split"] != "train"][:300] + _owl_va[:400]

dev = "cuda" if torch.cuda.is_available() else "cpu"; log("device", dev, torch.cuda.get_device_name(0) if dev == "cuda" else "")
net = BallNet3(); net.load_state_dict(torch.load(INIT, map_location="cpu", weights_only=True)); net.to(dev)
base = ("stem", "l1", "l2")
opt = torch.optim.AdamW([{"params": [p for n, p in net.named_parameters() if n.startswith(base)], "lr": 3e-4},
                         {"params": [p for n, p in net.named_parameters() if not n.startswith(base)], "lr": 1.5e-3}], weight_decay=1e-4)
sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1.0, (i + 1) / 300) * 0.5 * (1 + math.cos(math.pi * min(i, ITERS) / ITERS)))
is_rf = lambda m: m["src"].startswith("roboflow"); is_owl = lambda m: m["src"].startswith("owl")
other = lambda m: m["src"] not in ("teamtrack", "deepsport") and not is_rf(m) and not is_owl(m)
groups = {"tt_pos": [m for m in tr if m["ball"] and m["src"] == "teamtrack"],
          "our_pos": [m for m in tr if m["ball"] and other(m)],
          "ds_pos": [m for m in tr if m["ball"] and m["src"] == "deepsport"],
          "rf_pos": [m for m in tr if m["ball"] and is_rf(m)],
          "owl_pos": [m for m in tr if m["ball"] and is_owl(m)],
          "tt_neg": [m for m in tr if not m["ball"] and m["src"] == "teamtrack"],
          "our_neg": [m for m in tr if not m["ball"] and other(m) and not m.get("hard")],
          "ds_neg": [m for m in tr if not m["ball"] and m["src"] == "deepsport"],
          "rf_neg": [m for m in tr if not m["ball"] and is_rf(m)],
          "owl_neg": [m for m in tr if not m["ball"] and is_owl(m)],
          "hard_neg": [m for m in tr if not m["ball"] and other(m) and m.get("hard")]}
# round 3 proportions (tt 16, our 30, ds 14 | tt 8, our 16, ds 6, hard 18) doubled, plus OWL; Roboflow 36 -> 6
MIX = {"tt_pos": 24, "our_pos": 48, "ds_pos": 18, "rf_pos": 6, "owl_pos": 56, "tt_neg": 12, "our_neg": 28, "ds_neg": 6, "rf_neg": 2, "owl_neg": 10, "hard_neg": 30}
MIX.update(json.loads(os.environ.get("R5_MIX", "{}")))
if len(groups["owl_pos"]) < 200:  # too few pseudo-labels: do not oversample a handful of tiles
    MIX["owl_pos"] = min(MIX["owl_pos"], max(0, len(groups["owl_pos"]) // 8))
if len(groups["owl_neg"]) < 100:
    MIX["owl_neg"] = min(MIX["owl_neg"], max(0, len(groups["owl_neg"]) // 8))
if SMOKE:
    MIX = {k: max(1, v // 12) for k, v in MIX.items()}
mix = {k: v for k, v in MIX.items() if groups[k] and v > 0}
log({k: len(v) for k, v in groups.items()}, "mix", mix, "batch", sum(mix.values()))
R5["groups"] = {k: len(v) for k, v in groups.items()}; R5["mix"] = mix

# preload every tile the stream can draw into one byte buffer (shared by the forked workers, no per-file I/O)
used = [m for k in mix for m in groups[k]]


def _read_bytes(m):
    try:
        with open(path_of(m), "rb") as fh:
            return fh.read()
    except OSError:
        return b""


from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(32) as ex:
    blobs = list(ex.map(_read_bytes, used, chunksize=64))
offs = np.zeros(len(used) + 1, np.int64); offs[1:] = np.cumsum([len(b) for b in blobs])
BUF = np.frombuffer(b"".join(blobs), np.uint8); del blobs
for i, m in enumerate(used):
    m["_k"] = i
for k in mix:
    groups[k] = [m for m in groups[k] if offs[m["_k"] + 1] > offs[m["_k"]]]
log("preloaded", len(used), "tiles", round(len(BUF) / 1e9, 2), "GB")
S_IN = 256


def fast_load(m):
    """Decode only: three frames resized to 256 wide, ball scaled with them; the native scale factor goes along
    so the GPU zoom keeps the ball at its true pixel size."""
    k = m["_k"]; t = cv2.imdecode(BUF[offs[k]:offs[k + 1]], cv2.IMREAD_COLOR)
    w = t.shape[1] // 3; h = t.shape[0]; f = S_IN / w
    x = np.concatenate([cv2.resize(t[:, j * w:(j + 1) * w], (S_IN, round(h * f))) for j in range(3)], 2)
    if x.shape[0] != S_IN:
        x = cv2.copyMakeBorder(x[:S_IN], 0, max(0, S_IN - x.shape[0]), 0, 0, cv2.BORDER_REFLECT) if x.shape[0] < S_IN else x[:S_IN]
    b = m["ball"]; ball = [b[0] * f, b[1] * f, 1.0] if b else [-1.0, -1.0, 0.0]
    return x, np.array(ball + [f], np.float32)  # BGR kept; swapped on the GPU


class Stream(IterableDataset):
    def __iter__(self):
        wi = torch.utils.data.get_worker_info(); seed = 1234 + (wi.id if wi else 0)
        random.seed(seed); np.random.seed(seed); cv2.setNumThreads(1); torch.set_num_threads(1)
        while True:
            ms = [m for k, v in mix.items() for m in random.choices(groups[k], k=v)]
            xs, bs = zip(*[fast_load(m) for m in ms])
            yield torch.from_numpy(np.stack(xs)), torch.from_numpy(np.stack(bs))


KAX = torch.tensor([1.0, 1.0, 1.0], device=dev) / math.sqrt(3)


def hue_matrices(theta):
    c, s = torch.cos(theta), torch.sin(theta); K = KAX
    kx = torch.tensor([[0, -K[2], K[1]], [K[2], 0, -K[0]], [-K[1], K[0], 0]], device=dev)
    I = torch.eye(3, device=dev); kk = torch.outer(K, K)
    return c[:, None, None] * I + s[:, None, None] * kx + (1 - c)[:, None, None] * kk


def gpu_augment(x8, b, T=192):
    """uint8 BGR N,256,256,9 + (bx,by,valid,native) -> float RGB N,9,192,192 in 0..255 and N,1,48,48 heat."""
    n = x8.shape[0]; x = x8.to(dev, non_blocking=True).permute(0, 3, 1, 2).float()
    x = x[:, [2, 1, 0, 5, 4, 3, 8, 7, 6]]  # BGR -> RGB per frame
    b = b.to(dev); rev = torch.rand(n, device=dev) < 0.5
    x = torch.where(rev[:, None, None, None], x[:, [6, 7, 8, 3, 4, 5, 0, 1, 2]], x)
    zoom = torch.empty(n, device=dev).uniform_(0.7, 1.5); wr = T * b[:, 3] / zoom  # input pixels covered by the output
    valid = b[:, 2] > 0
    u = torch.empty(n, device=dev).uniform_(12, T - 12); v = torch.empty(n, device=dev).uniform_(12, T - 12)
    ox = torch.where(valid, b[:, 0] - u * wr / T, torch.rand(n, device=dev) * (S_IN - wr).clamp(min=0))
    oy = torch.where(valid, b[:, 1] - v * wr / T, torch.rand(n, device=dev) * (S_IN - wr).clamp(min=0))
    ox = torch.minimum(torch.maximum(ox, torch.zeros_like(ox)), (S_IN - wr).clamp(min=0)); oy = torch.minimum(torch.maximum(oy, torch.zeros_like(oy)), (S_IN - wr).clamp(min=0))
    flip = torch.rand(n, device=dev) < 0.5
    a = wr / S_IN; tx = (2 * ox + wr) / S_IN - 1; ty = (2 * oy + wr) / S_IN - 1
    theta = torch.zeros(n, 2, 3, device=dev); theta[:, 0, 0] = torch.where(flip, -a, a); theta[:, 0, 2] = tx; theta[:, 1, 1] = a; theta[:, 1, 2] = ty
    grid = F.affine_grid(theta, (n, 9, T, T), align_corners=False); x = F.grid_sample(x, grid, mode="bilinear", padding_mode="reflection", align_corners=False)
    cx = (b[:, 0] - ox) * T / wr; cy = (b[:, 1] - oy) * T / wr; cx = torch.where(flip, T - cx, cx)
    R = hue_matrices(torch.rand(n, device=dev) * 2 * math.pi)
    xr = x.view(n, 3, 3, T, T); xr = torch.einsum("nij,nfjhw->nfihw", R, xr)
    grey = xr.mean(dim=2, keepdim=True); sat = torch.empty(n, 1, 1, 1, 1, device=dev).uniform_(0.6, 1.4); xr = grey + sat * (xr - grey)
    xr = xr * torch.empty(n, 1, 1, 1, 1, device=dev).uniform_(0.7, 1.3) + torch.empty(n, 1, 1, 1, 1, device=dev).uniform_(-25, 25)
    x = xr.reshape(n, 9, T, T).clamp(0, 255)
    yy, xx = torch.meshgrid(torch.arange(48, device=dev, dtype=torch.float32), torch.arange(48, device=dev, dtype=torch.float32), indexing="ij")
    inside = valid & (cx >= 0) & (cx < T) & (cy >= 0) & (cy < T)
    heat = torch.exp(-(((xx[None] - (cx / 4)[:, None, None]) ** 2 + (yy[None] - (cy / 4)[:, None, None]) ** 2) / (2 * 1.2 ** 2))) * inside[:, None, None]
    return x, heat[:, None]


def evaluate_dev(net):
    net.eval(); res = {}
    with torch.no_grad():
        for k in range(0, len(va), 128):
            ms = va[k:k + 128]; xs, bs = zip(*[load_val(m) for m in ms])
            x = torch.from_numpy(np.stack(xs)).permute(0, 3, 1, 2).float().to(dev)
            hm = torch.sigmoid(net(x))[:, 0].float().cpu().numpy()
            for m, ball, h in zip(ms, bs, hm):
                g = res.setdefault(m["src"].split("_")[0], {"pos": [], "neg": []})
                yx = np.unravel_index(h.argmax(), h.shape); s = float(h.max())
                if ball:
                    g["pos"].append(s if np.hypot(yx[1] * 4 + 2 - ball[0], yx[0] * 4 + 2 - ball[1]) < 8 else 0.0)
                else:
                    g["neg"].append(s)
    net.train()
    return {src: {t: (round(float((np.array(g["pos"]) >= t).mean()), 3) if g["pos"] else None,
                      round(float((np.array(g["neg"]) >= t).mean()), 4) if g["neg"] else None) for t in (0.3, 0.5)} for src, g in res.items()}


nw = 0 if SMOKE else max(2, (os.cpu_count() or 4))
loader = DataLoader(Stream(), batch_size=None, num_workers=nw, prefetch_factor=4 if nw else None, persistent_workers=nw > 0, pin_memory=dev == "cuda")
scaler = torch.amp.GradScaler("cuda", enabled=dev == "cuda")
R5["val"] = {"start": evaluate_dev(net)}; log("val at start:", R5["val"]["start"])
t0 = time.time(); OUTPT = f"{WORK}/ball_r5.pt"; it = 0; ADJ_AT = int(os.environ.get("R5_ADJ_AT", "300"))
for it, (xb, bb) in enumerate(loader, 1):
    x, h = gpu_augment(xb, bb)
    with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=dev == "cuda"):
        logit = net(x)
    loss = focal(logit.float(), h); opt.zero_grad(set_to_none=True); scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); sched.step()
    if it == ADJ_AT:  # fit the schedule into the time budget (eval and saving take about 3 %)
        per = (time.time() - t0) / ADJ_AT; left = BUDGET_S - (time.time() - T_START) - 600
        fit = int(left / per / 1.03)
        if fit < ITERS:
            log(f"{per:.2f} s/it: ITERS {ITERS} -> {max(fit, 600)} to stay in the budget"); ITERS = max(fit, 600)
        else:
            log(f"{per:.2f} s/it: {ITERS} iterations need about {ITERS * per / 3600:.1f} h")
        R5["s_per_it"] = round(per, 3); R5["iters_planned"] = ITERS; torch.save(net.state_dict(), OUTPT)
        json.dump(R5, open(f"{WORK}/r5_stats.json", "w"), indent=1, default=str)
    if it % 200 == 0:
        log(f"it {it} loss {loss.item():.3f} {time.time() - t0:.0f}s")
    if it % 2000 == 0 or it >= ITERS or time.time() - T_START > BUDGET_S - 300:
        R5["val"][it] = evaluate_dev(net); log("val (found, false alarm):", R5["val"][it])
        torch.save(net.state_dict(), OUTPT); R5["iters_done"] = it
        json.dump(R5, open(f"{WORK}/r5_stats.json", "w"), indent=1, default=str)
    if it >= ITERS or time.time() - T_START > BUDGET_S - 300:
        break
# tiles for later rounds on Kaggle (kernel source); not meant for download
with zipfile.ZipFile(f"{WORK}/owl_tiles.zip", "w", zipfile.ZIP_STORED) as z:
    z.write(f"{TMP}/owl/meta_owl.json", "meta_owl.json")
    for m in owl_meta:
        z.write(f"{TMP}/owl/img/{m['file']}", f"img/{m['file']}")
log("done", it, "iterations")

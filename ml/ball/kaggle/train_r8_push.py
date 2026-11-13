"""Round 8 of the 3-frame ball net: round 7 (train_r7_push.py) plus the owner's 1000 hand-labelled
confident round-7 peaks from segments round 7 never saw (labelling page "Ball oder nicht?", two
rounds of 500: 273 balls, 720 no ball, 7 unsure; ml/ball/README.md).

Why: on test set 2 round 7 has the ball as top peak in 35 %, but 54 % of the frames without a ball
carry a peak >= 0.5, and among its confident peaks in unseen segments only 27 % are balls. A crop
verifier on top did not help measurably (47 % of the test balls are not among the top 5 peaks at
all), so the labels go into the heatmap net itself:
- every labelled point becomes a 224 px native triplet tile cut from the segment video on Kaggle:
  "ball" a positive (target at the point), "none" a hard negative (no target), unless a labelled
  ball of the same frame lies in the tile (then that ball is the target);
- about one third of the games (every third game, sorted) is held out as the "human" validation
  group, so the hourly validation shows the effect on exactly these mistakes;
- groups human_pos / human_neg with their own share of the batch; start from ball_r7.pt.

    python ml/ball/kaggle/train_r8_push.py HUMAN_LABELS_JSON WORKDIR   # then: kaggle kernels push -p WORKDIR
HUMAN_LABELS_JSON: [{id, game, video: "<dataset>/<file>", frame, gap, x, y, state}, ...]
"""
import json, subprocess, sys, tempfile
from pathlib import Path

here = Path(__file__).resolve().parent
labels = [l for l in json.load(open(sys.argv[1])) if l["state"] in ("ball", "none")]
work = Path(sys.argv[2]); work.mkdir(parents=True, exist_ok=True)
games = sorted({l["game"] for l in labels})
val_games = set(games[1::3])
human = [{"video": l["video"].split("/", 1)[1], "frame": int(l["frame"]), "gap": int(l["gap"]),
          "x": float(l["x"]), "y": float(l["y"]), "ball": l["state"] == "ball", "game": l["game"],
          "split": "val" if l["game"] in val_games else "train"} for l in labels]

with tempfile.TemporaryDirectory() as tmp:
    subprocess.run([sys.executable, str(here / "train_r7_push.py"), tmp], check=True, stdout=subprocess.DEVNULL)
    src = (Path(tmp) / "kaggle_r7.py").read_text()
    meta = json.loads((Path(tmp) / "kernel-metadata.json").read_text())


def rep(old: str, new: str, count: int = 1) -> None:
    global src
    n = src.count(old)
    if n != count:
        raise SystemExit(f"patch anchor found {n} times (want {count}): {old[:70]!r}")
    src = src.replace(old, new)


for a, b in (("ball_r7.pt", "ball_r8.pt"), ("r7_out.zip", "r8_out.zip"), ("r7_stats.json", "r8_stats.json"),
             ("r7_review_", "r8_review_"), ("owl_tiles_r7.zip", "owl_tiles_r8.zip")):
    src = src.replace(a, b)
rep('INIT = (glob.glob(INP + "/**/ball_r6.pt", recursive=True)',
    'INIT = (glob.glob(INP + "/**/ball_r7.pt", recursive=True) or glob.glob(INP + "/**/ball_r6.pt", recursive=True)')

# human tiles: cut on Kaggle from the segment videos, before training starts
rep("# ------------------------------------------------------------------ 2. training",
    "HUMAN = json.loads(r'''" + json.dumps(human) + "''')\n\n\n" + '''def build_human():
    """The owner's labelled peaks as 224 px native triplet tiles (see train_r8_push.py)."""
    os.makedirs(f"{TMP}/human/img", exist_ok=True)
    vids = {os.path.basename(a): a for a in glob.glob(INP + "/**/*.mp4", recursive=True)}
    by_frame = defaultdict(list)
    for h in HUMAN:
        by_frame[(h["video"], h["frame"], h["gap"])].append(h)
    rng = random.Random(8); out = []; st = defaultdict(int)
    for (video, f, G), hs in sorted(by_frame.items()):
        path = vids.get(video)
        if not path:
            st["missing_video"] += 1; continue
        cap = cv2.VideoCapture(path); cap.set(cv2.CAP_PROP_POS_FRAMES, f - G); fr = {}
        for k in range(2 * G + 1):
            ok, im = cap.read()
            if not ok:
                break
            if k in (0, G, 2 * G):
                fr[f - G + k] = cv2.resize(im, (1280, round(im.shape[0] * 1280 / im.shape[1])), interpolation=cv2.INTER_AREA)
        cap.release()
        ts = (f - G, f, f + G)
        if any(t not in fr for t in ts):
            st["short_read"] += 1; continue
        balls = [h for h in hs if h["ball"]]
        for i, h in enumerate(hs):
            img, x0, y0 = tile_at(fr, ts, h["x"], h["y"], rng)
            T = CFG["TILE"]
            inside = [b for b in balls if x0 <= b["x"] < x0 + T and y0 <= b["y"] < y0 + T]
            if len(inside) > 1 and max(math.hypot(b["x"] - inside[0]["x"], b["y"] - inside[0]["y"]) for b in inside) > 12:
                st["two_balls"] += 1; continue  # one target per tile
            fn = f"human_{video[:-4]}_{f}_{i}.jpg"
            cv2.imwrite(f"{TMP}/human/img/{fn}", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
            if inside:
                b = inside[0]
                out.append({"file": fn, "root": f"{TMP}/human", "split": h["split"], "src": "human", "tile": T,
                            "ball": [round(b["x"] - x0, 1), round(b["y"] - y0, 1), 12.0]})
                st["pos"] += 1
            else:
                out.append({"file": fn, "root": f"{TMP}/human", "split": h["split"], "src": "human", "tile": T,
                            "ball": None, "hard": True})
                st["neg"] += 1
    log("human tiles", dict(st))
    return out, dict(st)


human_meta, R6["human"] = build_human()

# ------------------------------------------------------------------ 2. training''')
rep("tr = tr + _seq + _dsp + [m for m in owl_meta + mine_meta if m[\"split\"] == \"train\"]",
    "tr = tr + _seq + _dsp + [m for m in owl_meta + mine_meta + human_meta if m[\"split\"] == \"train\"]")
rep("va = va + _owl_va[:400] + _mine_va[:400]",
    "va = va + _owl_va[:400] + _mine_va[:400] + [m for m in human_meta if m[\"split\"] != \"train\"]")
rep('other = lambda m: m["src"] not in ("teamtrack", "deepsport")',
    'other = lambda m: m["src"] not in ("teamtrack", "deepsport", "human")')
rep('          "hard_neg": [m for m in tr if not m["ball"] and other(m) and m.get("hard")]}',
    '          "hard_neg": [m for m in tr if not m["ball"] and other(m) and m.get("hard")],\n'
    '          "human_pos": [m for m in tr if m["ball"] and m["src"] == "human"],\n'
    '          "human_neg": [m for m in tr if not m["ball"] and m["src"] == "human"]}')
rep('"owl_neg": 20, "mine_neg": 6, "hard_neg": 36}',
    '"owl_neg": 20, "mine_neg": 6, "hard_neg": 36, "human_pos": 12, "human_neg": 28}')
# the human groups are small: never cut their share to len // 8 like the pseudo-label groups
src = '"""Round 8: generated by train_r8_push.py from train_r7_push.py / train_r6.py."""\n' + src

(work / "kaggle_r8.py").write_text(src)
meta.update(id="lukasde1000/handball-ball-r8", title="handball ball r8", code_file="kaggle_r8.py")
(work / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
print(work, len(human), "labels;", len(val_games), "of", len(games), "games held out;",
      sum(h["ball"] for h in human), "balls")

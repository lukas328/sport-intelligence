"""Round 6 of the 3-frame ball net. Same data idea as round 5/5b (never finished), made robust against being cut off.

Why rounds 5 and 5b produced nothing: both logs stop right after "val at start" (r5 at 23 min, r5b at 2.9 h), while
the kernels kept running for hours: not one training step was ever logged (round 3 logged every 200 steps). The
multi-process DataLoader (forked after a multiprocessing Pool, a 32-thread preload and OpenCV/CUDA use in the parent)
never delivered a batch; the local smoke tests ran without workers and missed it. Here batches come from threads
(OpenCV releases the GIL while decoding), nothing forks after CUDA is up, and a heartbeat dumps the stacks if the
loop stalls.

Data (anything within 2 s of a test-half or unsplit labelled frame of the user's benchmark is dropped everywhere):
- round 3 data: TeamTrack, own labelled tiles, the user's train-half frames and ball paths, DeepSport. No Roboflow
  still frames (round 4 showed they hurt).
- OWLv2 pseudo-labels from both OWL sources: kernel handball-ball-owl (segments b01..b03) and the Modal run
  handball-gpu-owl-20261105-1449 (189 segments of l01, l02). Kept when 3 of the 5 burst frames link with score
  >= 0.35, the best box >= 0.45, the chain moves (frame, camera, own surroundings) and does not sit on a fixed spot
  (train_r5.py logic, unchanged). Persistent still spots become hard negatives.
- mined tracklets (kernel handball-ball-mine, ~65 % real balls by eye), confirmed by OWLv2: up to MINE_PER_TRK tiles
  per tracklet are checked on the GPU(s) while the CPU cuts the OWL tiles; a tracklet counts when half its checked
  tiles have an OWL box >= 0.3 near the mined ball, and only those tiles become positives.

Robustness: whole kernel inside R6_BUDGET_H (9 h; Kaggle stops GPU sessions at 12 h). ITERS is fitted to the
measured s/it after 300 steps. Every hour: checkpoint + small eval to /kaggle/working (kept only if the kernel
completes) AND the fp16 checkpoint as base64 lines "R6CKPT ..." in the log (the log survives a cancel; rebuild with
ml/ball/kaggle/ckpt_from_log.py). Outputs: r6_out.zip (ball_r6.pt, r6_stats.json, review sheets; one file to
download), plus owl_tiles_r6.zip (tiles for later rounds as a kernel source, not for download)."""
import base64, faulthandler, glob, io, json, math, os, queue, random, re, subprocess, sys, threading, time, zipfile, zlib
from collections import defaultdict
from dataclasses import dataclass, field
from multiprocessing import Pool
import cv2, numpy as np

T_START = time.time()
INP = os.environ.get("R6_INPUT", "/kaggle/input")
WORK = os.environ.get("R6_WORK", "/kaggle/working")
TMP = os.environ.get("R6_TMP", "/tmp/r6")
BUDGET_S = float(os.environ.get("R6_BUDGET_H", "9.0")) * 3600  # whole kernel
RESERVE_S = 1200  # final eval, zips, notebook conversion
SMOKE = bool(os.environ.get("R6_SMOKE"))  # local test: CPU, few iterations
os.makedirs(WORK, exist_ok=True); os.makedirs(f"{TMP}/owl/img", exist_ok=True)
faulthandler.enable()
def log(*a): print(f"[{time.time() - T_START:6.0f}s]", *a, flush=True)
def left_s(): return BUDGET_S - (time.time() - T_START)

# ------------------------------------------------------------------ 0. test-half exclusion (+-2 s, all clips 30 fps)
# from labelpage db2 labels + ball3/user_split.json: frames of the test half and unsplit frames, per video
TEST_FRAMES = {"cb_seg_1080": [1367, 1626, 2373, 3569, 4131, 5539, 6239, 7575], "ch_nlb_2017_horgen_moehlin": [2058, 3061, 3274, 6437, 7018, 7480, 8126], "ch_nlb_2017_horgen_staefa": [305, 1792, 3601, 3642, 4569, 5132, 7383], "ch_spl2_2024_leimental_arbon": [1577, 2083, 3402, 4186, 5248, 5669, 6868], "eisenach_wetzlar_2": [578, 1868, 2533, 3225, 3316], "uznach_dietikon_s0": [1675, 2635, 3851, 3964, 4310, 4735, 5179], "uznach_dietikon_s2": [442, 637, 892, 1311, 1708, 3395, 4562, 5027], "uznach_dietikon_s3": [187, 396, 2131, 2822, 3896, 4402, 5062], "uznach_dietikon_s4": [393, 725, 1033, 2031, 2428, 2732, 3430, 4665]}
USER_LABELS = {"cottbus_seg_1352":["cb_seg_1080",1352],"cottbus_seg_1367":["cb_seg_1080",1367],"cottbus_seg_1626":["cb_seg_1080",1626],"cottbus_seg_2234":["cb_seg_1080",2234],"cottbus_seg_2373":["cb_seg_1080",2373],"cottbus_seg_3569":["cb_seg_1080",3569],"cottbus_seg_404":["cb_seg_1080",404],"cottbus_seg_4131":["cb_seg_1080",4131],"cottbus_seg_5004":["cb_seg_1080",5004],"cottbus_seg_5539":["cb_seg_1080",5539],"cottbus_seg_6190":["cb_seg_1080",6190],"cottbus_seg_6239":["cb_seg_1080",6239],"cottbus_seg_6477":["cb_seg_1080",6477],"cottbus_seg_7575":["cb_seg_1080",7575],"cottbus_seg_8075":["cb_seg_1080",8075],"eisenach_wetzlar_2_154":["eisenach_wetzlar_2",154],"eisenach_wetzlar_2_1868":["eisenach_wetzlar_2",1868],"eisenach_wetzlar_2_1899":["eisenach_wetzlar_2",1899],"eisenach_wetzlar_2_2533":["eisenach_wetzlar_2",2533],"eisenach_wetzlar_2_288":["eisenach_wetzlar_2",288],"eisenach_wetzlar_2_3225":["eisenach_wetzlar_2",3225],"eisenach_wetzlar_2_3316":["eisenach_wetzlar_2",3316],"eisenach_wetzlar_2_4000":["eisenach_wetzlar_2",4000],"eisenach_wetzlar_2_578":["eisenach_wetzlar_2",578],"eisenach_wetzlar_2_697":["eisenach_wetzlar_2",697],"horgen_moehlin_1131":["ch_nlb_2017_horgen_moehlin",1131],"horgen_moehlin_2058":["ch_nlb_2017_horgen_moehlin",2058],"horgen_moehlin_2295":["ch_nlb_2017_horgen_moehlin",2295],"horgen_moehlin_3061":["ch_nlb_2017_horgen_moehlin",3061],"horgen_moehlin_3236":["ch_nlb_2017_horgen_moehlin",3236],"horgen_moehlin_3274":["ch_nlb_2017_horgen_moehlin",3274],"horgen_moehlin_329":["ch_nlb_2017_horgen_moehlin",329],"horgen_moehlin_6437":["ch_nlb_2017_horgen_moehlin",6437],"horgen_moehlin_6619":["ch_nlb_2017_horgen_moehlin",6619],"horgen_moehlin_7018":["ch_nlb_2017_horgen_moehlin",7018],"horgen_moehlin_7043":["ch_nlb_2017_horgen_moehlin",7043],"horgen_moehlin_7480":["ch_nlb_2017_horgen_moehlin",7480],"horgen_moehlin_7767":["ch_nlb_2017_horgen_moehlin",7767],"horgen_moehlin_8126":["ch_nlb_2017_horgen_moehlin",8126],"horgen_moehlin_8487":["ch_nlb_2017_horgen_moehlin",8487],"horgen_staefa_156":["ch_nlb_2017_horgen_staefa",156],"horgen_staefa_1792":["ch_nlb_2017_horgen_staefa",1792],"horgen_staefa_2546":["ch_nlb_2017_horgen_staefa",2546],"horgen_staefa_305":["ch_nlb_2017_horgen_staefa",305],"horgen_staefa_3217":["ch_nlb_2017_horgen_staefa",3217],"horgen_staefa_3601":["ch_nlb_2017_horgen_staefa",3601],"horgen_staefa_3636":["ch_nlb_2017_horgen_staefa",3636],"horgen_staefa_3642":["ch_nlb_2017_horgen_staefa",3642],"horgen_staefa_4380":["ch_nlb_2017_horgen_staefa",4380],"horgen_staefa_4569":["ch_nlb_2017_horgen_staefa",4569],"horgen_staefa_470":["ch_nlb_2017_horgen_staefa",470],"horgen_staefa_5132":["ch_nlb_2017_horgen_staefa",5132],"horgen_staefa_6608":["ch_nlb_2017_horgen_staefa",6608],"horgen_staefa_7383":["ch_nlb_2017_horgen_staefa",7383],"horgen_staefa_838":["ch_nlb_2017_horgen_staefa",838],"leimental_arbon_1346":["ch_spl2_2024_leimental_arbon",1346],"leimental_arbon_1577":["ch_spl2_2024_leimental_arbon",1577],"leimental_arbon_1805":["ch_spl2_2024_leimental_arbon",1805],"leimental_arbon_2083":["ch_spl2_2024_leimental_arbon",2083],"leimental_arbon_2355":["ch_spl2_2024_leimental_arbon",2355],"leimental_arbon_3402":["ch_spl2_2024_leimental_arbon",3402],"leimental_arbon_398":["ch_spl2_2024_leimental_arbon",398],"leimental_arbon_4186":["ch_spl2_2024_leimental_arbon",4186],"leimental_arbon_4570":["ch_spl2_2024_leimental_arbon",4570],"leimental_arbon_5248":["ch_spl2_2024_leimental_arbon",5248],"leimental_arbon_5599":["ch_spl2_2024_leimental_arbon",5599],"leimental_arbon_5669":["ch_spl2_2024_leimental_arbon",5669],"leimental_arbon_6661":["ch_spl2_2024_leimental_arbon",6661],"leimental_arbon_6868":["ch_spl2_2024_leimental_arbon",6868],"leimental_arbon_7027":["ch_spl2_2024_leimental_arbon",7027],"uznach_dietikon_s0_1662":["uznach_dietikon_s0",1662],"uznach_dietikon_s0_1675":["uznach_dietikon_s0",1675],"uznach_dietikon_s0_1705":["uznach_dietikon_s0",1705],"uznach_dietikon_s0_2635":["uznach_dietikon_s0",2635],"uznach_dietikon_s0_3808":["uznach_dietikon_s0",3808],"uznach_dietikon_s0_3851":["uznach_dietikon_s0",3851],"uznach_dietikon_s0_3855":["uznach_dietikon_s0",3855],"uznach_dietikon_s0_3964":["uznach_dietikon_s0",3964],"uznach_dietikon_s0_4047":["uznach_dietikon_s0",4047],"uznach_dietikon_s0_4310":["uznach_dietikon_s0",4310],"uznach_dietikon_s0_4343":["uznach_dietikon_s0",4343],"uznach_dietikon_s0_4735":["uznach_dietikon_s0",4735],"uznach_dietikon_s0_4961":["uznach_dietikon_s0",4961],"uznach_dietikon_s0_5179":["uznach_dietikon_s0",5179],"uznach_dietikon_s0_921":["uznach_dietikon_s0",921],"uznach_dietikon_s2_1311":["uznach_dietikon_s2",1311],"uznach_dietikon_s2_1440":["uznach_dietikon_s2",1440],"uznach_dietikon_s2_1708":["uznach_dietikon_s2",1708],"uznach_dietikon_s2_272":["uznach_dietikon_s2",272],"uznach_dietikon_s2_3395":["uznach_dietikon_s2",3395],"uznach_dietikon_s2_3860":["uznach_dietikon_s2",3860],"uznach_dietikon_s2_442":["uznach_dietikon_s2",442],"uznach_dietikon_s2_4478":["uznach_dietikon_s2",4478],"uznach_dietikon_s2_4562":["uznach_dietikon_s2",4562],"uznach_dietikon_s2_493":["uznach_dietikon_s2",493],"uznach_dietikon_s2_5027":["uznach_dietikon_s2",5027],"uznach_dietikon_s2_5192":["uznach_dietikon_s2",5192],"uznach_dietikon_s2_637":["uznach_dietikon_s2",637],"uznach_dietikon_s2_667":["uznach_dietikon_s2",667],"uznach_dietikon_s2_892":["uznach_dietikon_s2",892],"uznach_dietikon_s3_1750":["uznach_dietikon_s3",1750],"uznach_dietikon_s3_187":["uznach_dietikon_s3",187],"uznach_dietikon_s3_2064":["uznach_dietikon_s3",2064],"uznach_dietikon_s3_2131":["uznach_dietikon_s3",2131],"uznach_dietikon_s3_2559":["uznach_dietikon_s3",2559],"uznach_dietikon_s3_2822":["uznach_dietikon_s3",2822],"uznach_dietikon_s3_3758":["uznach_dietikon_s3",3758],"uznach_dietikon_s3_3896":["uznach_dietikon_s3",3896],"uznach_dietikon_s3_3950":["uznach_dietikon_s3",3950],"uznach_dietikon_s3_396":["uznach_dietikon_s3",396],"uznach_dietikon_s3_4244":["uznach_dietikon_s3",4244],"uznach_dietikon_s3_4402":["uznach_dietikon_s3",4402],"uznach_dietikon_s3_4991":["uznach_dietikon_s3",4991],"uznach_dietikon_s3_5062":["uznach_dietikon_s3",5062],"uznach_dietikon_s3_846":["uznach_dietikon_s3",846],"uznach_dietikon_s4_1033":["uznach_dietikon_s4",1033],"uznach_dietikon_s4_1034":["uznach_dietikon_s4",1034],"uznach_dietikon_s4_2031":["uznach_dietikon_s4",2031],"uznach_dietikon_s4_2230":["uznach_dietikon_s4",2230],"uznach_dietikon_s4_2428":["uznach_dietikon_s4",2428],"uznach_dietikon_s4_2517":["uznach_dietikon_s4",2517],"uznach_dietikon_s4_2732":["uznach_dietikon_s4",2732],"uznach_dietikon_s4_3430":["uznach_dietikon_s4",3430],"uznach_dietikon_s4_3482":["uznach_dietikon_s4",3482],"uznach_dietikon_s4_393":["uznach_dietikon_s4",393],"uznach_dietikon_s4_4351":["uznach_dietikon_s4",4351],"uznach_dietikon_s4_4665":["uznach_dietikon_s4",4665],"uznach_dietikon_s4_4763":["uznach_dietikon_s4",4763],"uznach_dietikon_s4_725":["uznach_dietikon_s4",725],"uznach_dietikon_s4_831":["uznach_dietikon_s4",831]}
EXCL = 60
# games a test clip may have been cut from (5-minute clips of these games): never use their segments for pseudo-labels
TEST_GAMES = [("horgen", "moehlin", "2017"), ("horgen", "staefa", "2017"), ("leimental", "arbon", "2024")]


def norm(v):
    return re.sub("[^a-z0-9]", "_", v.split("/")[-1].rsplit(".", 1)[0].lower())


def near_test(v, f):
    return any(abs(f - t) <= EXCL for t in TEST_FRAMES.get(norm(v), []))


def test_game(name):
    n = name.lower()
    return any(all(k in n for k in g) for g in TEST_GAMES) or norm(name) in TEST_FRAMES


def where(m):
    """(video, frame) of a training tile when the file name or meta says it, else None."""
    fn = m["file"]
    if "vid" in m and "frame" in m:
        return m["vid"], int(m["frame"])
    if fn.startswith("seq_"):
        r = re.match(r"seq_(.+)_(\d+)_(\d+)_[a-z]+\d*\.jpg$", fn); return (r.group(1), int(r.group(3))) if r else None
    if fn.startswith("usr_"):
        r = re.match(r"usr_(.+)_[a-z]+\d*\.jpg$", fn); u = USER_LABELS.get(r.group(1)) if r else None; return tuple(u) if u else None
    if fn.startswith("tri_cand_") and m.get("vid"):
        r = re.match(r"tri_cand_.+_(\d+)_\d+\.jpg$", fn); return (m["vid"], int(r.group(1))) if r else None
    return None


def drop_test(ms, tag, stats):
    out = []
    for m in ms:
        w = where(m)
        if w and near_test(*w):
            stats[tag] = stats.get(tag, 0) + 1; continue
        out.append(m)
    return out


R6 = {"excluded_near_test": {}}

# ------------------------------------------------------------------ 1b (started first). mined tiles -> OWLv2 on the GPU(s)
MCFG = dict(NEAR=12.0, MAX_SIDE=48.0, TILE_MIN=0.3, TRK_PASS=0.5, TRK_FAIL=0.2, NEG_SPOT=0.1, NEG_ANY=0.3, NEG_MOTION=0.2,
            NEG_PER_TRK=3, NEG_PER_SEG=80, MIN_VERIFIED=3, PER_TRK=6, BUDGET_H=1.3, BATCH=8, VAL_SEG="magdeburg_rostock_s4")
MCFG.update({k: type(v)(os.environ[f"R6_{k}"]) for k, v in MCFG.items() if f"R6_{k}" in os.environ})
WORKER_SRC = r'''
import json, os, sys, time, cv2, numpy as np, torch
items = json.load(open(sys.argv[1])); out = sys.argv[2]; budget = float(sys.argv[3]); C = json.loads(sys.argv[4])
from transformers import Owlv2ForObjectDetection, Owlv2Processor
dev = "cuda"; name = "google/owlv2-base-patch16-ensemble"
proc = Owlv2Processor.from_pretrained(name)
model = Owlv2ForObjectDetection.from_pretrained(name, torch_dtype=torch.float16).to(dev).eval()
tok = proc(text=[["a photo of a handball", "a ball", "a small ball in the air"]], return_tensors="pt")
ids, mask = tok["input_ids"].to(dev), tok["attention_mask"].to(dev)
MEAN = torch.tensor([0.48145466, 0.4578275, 0.40821073], device=dev).view(1, 3, 1, 1)
STD = torch.tensor([0.26862954, 0.26130258, 0.27577711], device=dev).view(1, 3, 1, 1)
t0 = time.time(); res = {}; B = int(C["BATCH"])
def flush():
    json.dump(res, open(out + ".tmp", "w")); os.replace(out + ".tmp", out)
for k in range(0, len(items), B):
    if time.time() - t0 > budget:
        print("owl worker: budget reached after", len(res), "tiles", flush=True); break
    chunk = items[k:k + B]; ims, sides = [], []
    for m in chunk:
        t = cv2.imread(m["path"]); w = t.shape[1] // 3; c = t[:, w:2 * w]; side = max(c.shape[:2])
        c = cv2.copyMakeBorder(c, 0, side - c.shape[0], 0, side - c.shape[1], cv2.BORDER_CONSTANT, value=(128, 128, 128))
        ims.append(cv2.resize(cv2.cvtColor(c, cv2.COLOR_BGR2RGB), (960, 960), interpolation=cv2.INTER_LINEAR)); sides.append(side)
    x = torch.from_numpy(np.stack(ims)).to(dev).permute(0, 3, 1, 2).float() / 255
    x = ((x - MEAN) / STD).to(model.dtype); n = x.shape[0]
    with torch.no_grad():
        o = model(input_ids=ids.repeat(n, 1), attention_mask=mask.repeat(n, 1), pixel_values=x)
    sc = o.logits.float().sigmoid().max(-1).values; bx = o.pred_boxes.float()
    for i, m in enumerate(chunk):
        b = bx[i] * sides[i]; ok = torch.maximum(b[:, 2], b[:, 3]) <= C["MAX_SIDE"]
        d = torch.hypot(b[:, 0] - m["ball_in_tile"][0], b[:, 1] - m["ball_in_tile"][1])
        s_ok = torch.where(ok, sc[i], torch.zeros_like(sc[i]))
        res[m["file"]] = [round(float(torch.where(d <= C["NEAR"], s_ok, torch.zeros_like(s_ok)).max()), 3), round(float(s_ok.max()), 3)]
    if len(res) % 2000 < B:
        flush(); print("owl worker", len(res), "of", len(items), f"{time.time() - t0:.0f}s", flush=True)
flush(); print("owl worker done", len(res), f"{time.time() - t0:.0f}s", flush=True)
'''


def start_mined_owl():
    """Pick the tiles to check (test-near tracklets dropped), split them over the visible GPUs, start one worker
    process per GPU. Returns (tracklets, worker handles)."""
    ALL = glob.glob(INP + "/**/*", recursive=True)
    jpg = {os.path.basename(a): a for a in ALL if os.path.basename(a).startswith("mine_") and a.endswith(".jpg")
           and os.path.basename(os.path.dirname(a)) == "mined"}
    items = []
    for a in ALL:
        b = os.path.basename(a)
        if b.startswith("mined_") and b.endswith(".json"):
            items += json.load(open(a))
    log(len(items), "mined tiles,", len(jpg), "tile files")
    trk = defaultdict(list); st = defaultdict(lambda: defaultdict(int))
    for m in items:
        if m["file"] in jpg:
            m["path"] = jpg[m["file"]]; trk[m["tracklet"]].append(m)
    for t, ms in list(trk.items()):
        v = ms[0]["vid"]; st[v]["tracklets"] += 1; st[v]["tiles"] += len(ms)
        if any(near_test(v, m["frame"]) for m in ms):
            st[v]["excl_tracklets"] += 1; st[v]["excl_tiles"] += len(ms); del trk[t]
    keys = sorted(trk); random.Random(5).shuffle(keys)  # random order: a budget stop leaves an unbiased sample
    pick = {}
    for t in keys:
        ms = sorted(trk[t], key=lambda m: m["frame"]); n = MCFG["PER_TRK"]
        pick[t] = ms if len(ms) <= n else [ms[round(i * (len(ms) - 1) / (n - 1))] for i in range(n)]
    try:
        ngpu = len([l for l in subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True).stdout.splitlines() if l.startswith("GPU")])
    except Exception:
        ngpu = 0
    procs = []
    if ngpu and not os.environ.get("R6_FAKE_OWL"):
        open(f"{TMP}/owl_worker.py", "w").write(WORKER_SRC)
        for g in range(ngpu):
            its = [{k: m[k] for k in ("file", "path", "ball_in_tile")} for t in keys[g::ngpu] for m in pick[t]]
            json.dump(its, open(f"{TMP}/mined_items_{g}.json", "w"))
            env = {**os.environ, "CUDA_VISIBLE_DEVICES": str(g)}
            lf = open(f"{TMP}/owl_worker_{g}.log", "w")
            procs.append((subprocess.Popen([sys.executable, f"{TMP}/owl_worker.py", f"{TMP}/mined_items_{g}.json", f"{TMP}/mined_owl_{g}.json",
                                            str(MCFG["BUDGET_H"] * 3600), json.dumps(MCFG)], env=env, stdout=lf, stderr=subprocess.STDOUT), lf, len(its)))
        log("mined OWL check started on", ngpu, "GPU(s):", sum(p[2] for p in procs), "tiles of", len(keys), "tracklets")
    return trk, keys, pick, st, procs


def finish_mined_owl(trk, keys, pick, st, procs, deadline):
    for g, (p, lf, n) in enumerate(procs):
        try:
            p.wait(timeout=max(1, deadline - time.time()))
        except subprocess.TimeoutExpired:
            log("mined OWL worker", g, "past its deadline: stopped"); p.kill()
        lf.close(); log("worker", g, "log tail:", open(f"{TMP}/owl_worker_{g}.log").read()[-600:].replace("\n", " | "))
    scores = {}
    for g in range(len(procs)):
        try:
            scores.update(json.load(open(f"{TMP}/mined_owl_{g}.json")))
        except Exception as e:
            log("no OWL results from worker", g, e)
    if os.environ.get("R6_FAKE_OWL"):  # local test of the training path only
        for t in keys:
            for m in pick[t]:
                scores[m["file"]] = [0.5, 0.5] if m["score"] > 0.3 else [0.05, 0.05]
    meta = []; rng = random.Random(7)
    for t in keys:
        ms = [m for m in pick[t] if m["file"] in scores]; v = trk[t][0]["vid"]
        for m in ms:
            m["owl_near"], m["owl_any"] = scores[m["file"]]
        if len(ms) < MCFG["MIN_VERIFIED"]:
            continue
        st[v]["verified_tracklets"] += 1; st[v]["verified_tiles"] += len(ms)
        frac = sum(m["owl_near"] >= MCFG["TILE_MIN"] for m in ms) / len(ms)
        split = "val" if v == MCFG["VAL_SEG"] else "train"; src = f"mine_{v}"
        if frac >= MCFG["TRK_PASS"]:
            st[v]["kept_tracklets"] += 1
            for m in ms:
                if m["owl_near"] >= MCFG["TILE_MIN"]:
                    meta.append({"file": m["file"], "path": m["path"], "split": split, "ball": [float(m["ball_in_tile"][0]), float(m["ball_in_tile"][1]), 10.0],
                                 "src": src, "owl": m["owl_near"]}); st[v]["pos_tiles"] += 1
        elif frac <= MCFG["TRK_FAIL"]:
            st[v]["failed_tracklets"] += 1
            cand = [m for m in ms if m["owl_near"] < MCFG["NEG_SPOT"] and m["owl_any"] < MCFG["NEG_ANY"] and m.get("motion", 1.0) < MCFG["NEG_MOTION"]]
            for m in rng.sample(cand, min(len(cand), MCFG["NEG_PER_TRK"])):
                if st[v]["neg_tiles"] >= MCFG["NEG_PER_SEG"]:
                    break
                meta.append({"file": m["file"], "path": m["path"], "split": split, "ball": None, "src": src, "mine_spot": m["ball_in_tile"]})
                st[v]["neg_tiles"] += 1
    stats = {v: dict(d) for v, d in sorted(st.items())}; tot = defaultdict(int)
    for d in stats.values():
        for k, x in d.items():
            tot[k] += x
    log("mined verification", dict(tot), "OWL scores for", len(scores), "tiles")
    cells = []
    sample = rng.sample([m for t in keys for m in pick[t] if "owl_near" in m], min(64, len(scores)))
    for m in sorted(sample, key=lambda m: -m["owl_near"]):
        t = cv2.imread(m["path"]); w = t.shape[1] // 3; c = t[:, w:2 * w].copy(); x, y = int(m["ball_in_tile"][0]), int(m["ball_in_tile"][1])
        cv2.circle(c, (x, y), 14, (0, 255, 0) if m["owl_near"] >= MCFG["TILE_MIN"] else (0, 0, 255), 1)
        cv2.putText(c, f"{m['owl_near']:.2f}/{m['owl_any']:.2f}", (2, 12), 0, 0.4, (255, 255, 255), 1); cells.append(cv2.resize(c, (160, 160)))
    if cells:
        while len(cells) % 8:
            cells.append(np.zeros_like(cells[0]))
        cv2.imwrite(f"{WORK}/r6_review_mined.jpg", cv2.vconcat([cv2.hconcat(cells[i:i + 8]) for i in range(0, len(cells), 8)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
    return meta, {"cfg": MCFG, "total": dict(tot), "per_segment": stats, "owl_scored": len(scores)}


MINED = start_mined_owl()
MINED_DEADLINE = time.time() + MCFG["BUDGET_H"] * 3600 + 900  # model download + last batch

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
CFG.update({k: type(v)(os.environ[f"R6_{k}"]) for k, v in CFG.items() if f"R6_{k}" in os.environ})


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
    """Both OWL sources: any segs/*.json with bursts whose video is among the inputs (kernel handball-ball-owl for
    b01..b03, dataset handball-gpu-owl-20261105-1449 for l01/l02). Stops cutting at R6_OWL_CUT_H."""
    ALL = glob.glob(INP + "/**/*", recursive=True)
    vids = {os.path.basename(a)[:-4]: a for a in ALL if a.endswith(".mp4")}
    jsons, seen, skipped = [], set(), []
    for a in sorted(ALL):
        if not (a.endswith(".json") and os.path.basename(os.path.dirname(a)) == "segs"):
            continue
        try:
            d = json.load(open(a))
        except Exception:
            continue
        if not (isinstance(d, dict) and "bursts" in d):
            continue
        key = os.path.basename(d.get("file", ""))[:-4] or os.path.basename(a)[:-5]
        v = vids.get(key) or vids.get(os.path.basename(a)[:-5])
        if not v or key in seen:
            continue
        if test_game(key):
            skipped.append(key); continue
        seen.add(key); jsons.append((a, v, "l" if "handball-gpu-owl" in a else "b"))
    log(len(jsons), "OWL segment files with video,", len(vids), "videos; test games skipped:", skipped)
    games = defaultdict(set)
    for _, v, srcx in jsons:
        games[srcx].add(os.path.basename(v)[:-4].rsplit("_s", 1)[0])
    val_games = {sorted(g)[len(g) // 2] for g in games.values() if len(g) >= 6}  # one game per source held out
    log("games", {k: len(g) for k, g in games.items()}, "val games", sorted(val_games))
    args = [(j, v, os.path.basename(v)[:-4].rsplit("_s", 1)[0] in val_games) for j, v, _ in jsons]
    random.Random(3).shuffle(args)  # a time stop leaves a mix of both sources
    meta, stats, review = [], {}, []
    cut_at = T_START + float(os.environ.get("R6_OWL_CUT_H", "1.7")) * 3600
    pool = Pool(max(1, min(4, os.cpu_count() or 2)))
    try:
        for name, game, m, st, rv in pool.imap_unordered(process_segment, args):
            meta += m; stats[name] = st; review += rv
            log(name, {k: st.get(k, 0) for k in ("bursts", "confirmed", "pos_tiles", "neg_tiles")}, f"{len(stats)}/{len(args)}")
            if time.time() > cut_at:
                log("OWL tile cutting: time cap reached after", len(stats), "of", len(args), "segments"); break
    finally:
        pool.terminate(); pool.join()
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
    review_sheet(pos, f"{WORK}/r6_review_pos.jpg", 64); review_sheet(neg, f"{WORK}/r6_review_neg.jpg", 32)
    out = {"cfg": CFG, "segments_done": len(stats), "segments_found": len(args), "total": dict(tot),
           "per_game": {g: dict(v) for g, v in sorted(per_game.items())}, "val_games": sorted(val_games)}
    log("OWL confirmation total", dict(tot))
    return meta, out


owl_meta, R6["owl"] = build_owl()
json.dump(R6, open(f"{WORK}/r6_stats.json", "w"), indent=1, default=str)
mine_meta, R6["mined"] = finish_mined_owl(*MINED, deadline=MINED_DEADLINE)
json.dump(R6, open(f"{WORK}/r6_stats.json", "w"), indent=1, default=str)
if os.environ.get("R6_PREP_ONLY"):
    log("prep only: stop"); sys.exit(0)

# ------------------------------------------------------------------ 2. training (no DataLoader: thread feeder)
import torch, torch.nn as nn, torch.nn.functional as F, torchvision
from pathlib import Path
cv2.setNumThreads(1)
_D = os.path.dirname(glob.glob(INP + "/**/meta_tt.json", recursive=True)[0])
_D2 = os.path.dirname(glob.glob(INP + "/**/meta_seq.json", recursive=True)[0])
_DS = glob.glob(INP + "/**/basketball-instants-dataset.json", recursive=True)
_METAS = "meta_tt.json,meta_ourlab.json,meta_lab3.json,meta_user.json,meta_konstanz_wuerzburg.json,meta_uznach_dietikon.json,meta_eisenach_wetzlar.json,meta_leimental_frauenfeld.json,meta_muelheim_suedpfalz.json,meta_u20_sui_ger.json"
ITERS = int(os.environ.get("ITERS", "30000"))  # cap; fitted to the budget after ADJ_AT steps
INIT = (glob.glob(INP + "/**/ball_best.pt", recursive=True) or [_D + "/ball3a.pt"])[0]
log("data", _D, _D2, _DS, "init", INIT)
torch.set_num_threads(4); random.seed(0); np.random.seed(0); torch.manual_seed(0)
D = Path(_D); T = 192
meta = [m for f in _METAS.split(",") if os.path.exists(D / f) for m in json.load(open(D / f))]
if SMOKE:
    meta = [m for m in meta if os.path.exists(Path(m.get("root", D)) / ("cand" if m["file"].startswith(("cand_", "mine_")) else "img") / m["file"])]
meta = drop_test(meta, "round3_metas", R6["excluded_near_test"])
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
    if "path" in m:
        return Path(m["path"])
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
_seq = drop_test(json.load(open(_D2 + "/meta_seq.json")), "seq", R6["excluded_near_test"])
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
mine_meta = drop_test(mine_meta, "mined", R6["excluded_near_test"])
log("seq", len(_seq), "deepsport", len(_dsp), "owl", len(owl_meta), "mined", len(mine_meta), "excluded near test", R6["excluded_near_test"])
tr = tr + _seq + _dsp + [m for m in owl_meta + mine_meta if m["split"] == "train"]
_owl_va = [m for m in owl_meta if m["split"] != "train"]; random.shuffle(_owl_va)
if SMOKE:
    va = va[:200]
_mine_va = [m for m in mine_meta if m["split"] != "train"]; random.shuffle(_mine_va)
va = va + _owl_va[:400] + _mine_va[:400]

dev = "cuda" if torch.cuda.is_available() else "cpu"; log("device", dev, torch.cuda.get_device_name(0) if dev == "cuda" else "", "GPUs", torch.cuda.device_count())
net = BallNet3(); net.load_state_dict(torch.load(INIT, map_location="cpu", weights_only=True)); net.to(dev)
base = ("stem", "l1", "l2")
opt = torch.optim.AdamW([{"params": [p for n, p in net.named_parameters() if n.startswith(base)], "lr": 3e-4},
                         {"params": [p for n, p in net.named_parameters() if not n.startswith(base)], "lr": 1.5e-3}], weight_decay=1e-4)
sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1.0, (i + 1) / 300) * 0.5 * (1 + math.cos(math.pi * min(i, ITERS) / ITERS)))
is_owl = lambda m: m["src"].startswith("owl"); is_mine = lambda m: m["src"].startswith("mine_")
other = lambda m: m["src"] not in ("teamtrack", "deepsport") and not m["src"].startswith("roboflow") and not is_owl(m) and not is_mine(m)
groups = {"tt_pos": [m for m in tr if m["ball"] and m["src"] == "teamtrack"],
          "our_pos": [m for m in tr if m["ball"] and other(m)],
          "ds_pos": [m for m in tr if m["ball"] and m["src"] == "deepsport"],
          "owl_pos": [m for m in tr if m["ball"] and is_owl(m)],
          "mine_pos": [m for m in tr if m["ball"] and is_mine(m)],
          "tt_neg": [m for m in tr if not m["ball"] and m["src"] == "teamtrack"],
          "our_neg": [m for m in tr if not m["ball"] and other(m) and not m.get("hard")],
          "ds_neg": [m for m in tr if not m["ball"] and m["src"] == "deepsport"],
          "owl_neg": [m for m in tr if not m["ball"] and is_owl(m)],
          "mine_neg": [m for m in tr if not m["ball"] and is_mine(m)],
          "hard_neg": [m for m in tr if not m["ball"] and other(m) and m.get("hard")]}
# round 3 mix (kernel2: 16/30/14 pos, 8/16/6/18 neg) plus the pseudo-label groups; no Roboflow
MIX = {"tt_pos": 16, "our_pos": 30, "ds_pos": 14, "owl_pos": 36, "mine_pos": 24, "tt_neg": 8, "our_neg": 16, "ds_neg": 6, "owl_neg": 10, "mine_neg": 6, "hard_neg": 18}
MIX.update(json.loads(os.environ.get("R6_MIX", "{}")))
for g in ("owl_pos", "mine_pos"):
    if len(groups[g]) < 200:  # too few pseudo-labels: do not oversample a handful of tiles
        MIX[g] = min(MIX[g], max(0, len(groups[g]) // 8))
for g in ("owl_neg", "mine_neg"):
    if len(groups[g]) < 100:
        MIX[g] = min(MIX[g], max(0, len(groups[g]) // 8))
if SMOKE:
    MIX = {k: max(1, v // 12) for k, v in MIX.items()}
mix = {k: v for k, v in MIX.items() if groups[k] and v > 0}
log({k: len(v) for k, v in groups.items()}, "mix", mix, "batch", sum(mix.values()))
R6["groups"] = {k: len(v) for k, v in groups.items()}; R6["mix"] = mix

# preload every tile the feeder can draw into one byte buffer (no per-file I/O while training)
used = [m for k in mix for m in groups[k]]


def _read_bytes(m):
    try:
        with open(path_of(m), "rb") as fh:
            return fh.read()
    except OSError:
        return b""


blobs = [None] * len(used)
def _rd(k0):
    for k in range(k0, len(used), 8):
        blobs[k] = _read_bytes(used[k])
ths = [threading.Thread(target=_rd, args=(k,)) for k in range(8)]
[t.start() for t in ths]; [t.join() for t in ths]
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



class Feeder:
    """Batches built by threads (cv2 decode/resize release the GIL); a bounded queue in front of the GPU."""
    def __init__(s, n_threads, depth=8):
        s.q = queue.Queue(depth); s.stop = False
        s.th = [threading.Thread(target=s.run, args=(i,), daemon=True) for i in range(n_threads)]
        [t.start() for t in s.th]

    def run(s, i):
        rng = random.Random(1234 + i)
        while not s.stop:
            try:
                ms = [m for k, v in mix.items() for m in rng.choices(groups[k], k=v)]
                xs, bs = zip(*[fast_load(m) for m in ms])
                x = torch.from_numpy(np.stack(xs)); b = torch.from_numpy(np.stack(bs))
                if dev == "cuda":
                    x = x.pin_memory(); b = b.pin_memory()
                s.q.put((x, b))
            except Exception as e:  # a broken tile must not kill the feeder silently
                log("feeder error", repr(e)); time.sleep(0.1)

    def __iter__(s):
        while True:
            yield s.q.get()


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



OUTPT = f"{WORK}/ball_r6.pt"


def save_ckpt(tag, to_log):
    """Checkpoint to /kaggle/working; with to_log also as fp16 base64 lines in the log (survives a cancel)."""
    sd = {k: v.detach().cpu() for k, v in net.state_dict().items()}
    torch.save(sd, OUTPT); json.dump(R6, open(f"{WORK}/r6_stats.json", "w"), indent=1, default=str)
    if to_log:
        bio = io.BytesIO(); torch.save({k: (v.half() if v.is_floating_point() else v) for k, v in sd.items()}, bio)
        b64 = base64.b64encode(zlib.compress(bio.getvalue(), 6)).decode(); n = math.ceil(len(b64) / 60000)
        for i in range(n):
            print(f"R6CKPT {tag} {i + 1}/{n} {b64[i * 60000:(i + 1) * 60000]}", flush=True)
        log("checkpoint", tag, "in the log:", n, "lines")


feeder = Feeder(2 if SMOKE else max(2, (os.cpu_count() or 4)), depth=2 if SMOKE else 8)
batches = iter(feeder)
scaler = torch.amp.GradScaler("cuda", enabled=dev == "cuda")
R6["val"] = {"start": evaluate_dev(net)}; log("val at start:", R6["val"]["start"])
STATE = {"it": 0, "t": time.time()}


def heartbeat():
    last = -1
    while True:
        time.sleep(600)
        log("heartbeat it", STATE["it"], "queue", feeder.q.qsize())
        if STATE["it"] == last:
            log("no step for 10 min: stacks follow"); faulthandler.dump_traceback(all_threads=True)
        last = STATE["it"]


threading.Thread(target=heartbeat, daemon=True).start()
t0 = time.time(); it = 0; ADJ_AT = int(os.environ.get("R6_ADJ_AT", "300")); next_hour = time.time() + 3600; hour = 0
stop_at = T_START + BUDGET_S - RESERVE_S
for it in range(1, 10 ** 9):
    xb, bb = next(batches)
    x, h = gpu_augment(xb, bb)
    with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=dev == "cuda"):
        logit = net(x)
    loss = focal(logit.float(), h); opt.zero_grad(set_to_none=True); scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); sched.step()
    STATE["it"] = it
    if it in (1, 10, 50) or it % 200 == 0:
        log(f"it {it} loss {loss.item():.3f} {time.time() - t0:.0f}s")
    if it == ADJ_AT:  # fit the schedule into the time budget (hourly evals take about 1 %)
        per = (time.time() - t0) / ADJ_AT; fit = int((stop_at - time.time()) / per / 1.03)
        if fit < ITERS:
            log(f"{per:.3f} s/it: ITERS {ITERS} -> {max(fit, 600)} to stay in the budget"); ITERS = max(fit, 600)
        else:
            log(f"{per:.3f} s/it: {ITERS} iterations need about {ITERS * per / 3600:.1f} h")
        R6["s_per_it"] = round(per, 3); R6["iters_planned"] = ITERS; save_ckpt("adj", False)
    done = it >= ITERS or time.time() > stop_at
    if time.time() > next_hour and not done:
        hour += 1; next_hour += 3600
        R6["val"][it] = evaluate_dev(net); R6["iters_done"] = it; log(f"hour {hour} val (found, false alarm):", R6["val"][it])
        save_ckpt(f"h{hour}_it{it}", True)
    if done:
        break
feeder.stop = True
R6["val"][it] = evaluate_dev(net); R6["iters_done"] = it; R6["train_s"] = round(time.time() - t0)
log("final val (found, false alarm):", R6["val"][it])
save_ckpt(f"final_it{it}", True)
with zipfile.ZipFile(f"{WORK}/r6_out.zip", "w", zipfile.ZIP_DEFLATED) as z:  # the one file to download
    for f in ("ball_r6.pt", "r6_stats.json", "r6_review_pos.jpg", "r6_review_neg.jpg", "r6_review_mined.jpg"):
        if os.path.exists(f"{WORK}/{f}"):
            z.write(f"{WORK}/{f}", f)
log("r6_out.zip written")
# tiles for later rounds on Kaggle (kernel source); not meant for download
if left_s() > 300:
    with zipfile.ZipFile(f"{WORK}/owl_tiles_r6.zip", "w", zipfile.ZIP_STORED) as z:
        z.write(f"{TMP}/owl/meta_owl.json", "meta_owl.json")
        for f in sorted({m["file"] for m in owl_meta}):
            z.write(f"{TMP}/owl/img/{f}", f"img/{f}")
log("done", it, "iterations")

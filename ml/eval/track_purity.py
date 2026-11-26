"""Team purity of the player tracks on stored observations (dev clips only, never the end test).

    VIDEO=clip.mp4 python ml/eval/track_purity.py OBS_DIR VARIANT

OBS_DIR holds observations.npz, motion.npz (and play.json); VARIANT is "old" (no learned team
colours), "new" (product default) or a JSON of kit colours ({"home": "#c8102e", ...}). With VIDEO
set the camera motion is estimated again from the clip (motion files stored without samples).

Team purity of the final tracks: each torso look of a track is put to the nearer of two fixed
reference team colours (learned once from all looks on court, the same for every variant); a track
is mixed when at least 25 % of its looks (>= 20) sit on its minority side."""

import collections
import json
import os
import statistics
import sys
from pathlib import Path

import cv2
import numpy as np

from handball_gpu_worker.analysis import hex_to_bgr, play_intervals
from handball_vision import observe as learned
from handball_vision import pipeline
from handball_vision.detection import court_mask
from handball_vision.motion import CameraMotion
from handball_vision.teams import _feature, learn_kits

d, variant = Path(sys.argv[1]), sys.argv[2]
mot = CameraMotion.load(d / "motion.npz")
if os.environ.get("VIDEO"):
    from handball_vision.motion import MotionEstimator
    from handball_vision.pipeline import _open, iter_frames

    _, _, _, total = _open(Path(os.environ["VIDEO"]))
    est = MotionEstimator(keep_every=max(1, total // 30) if total else 25)
    for fr in iter_frames(Path(os.environ["VIDEO"])):
        est.add(fr)
    mot = est.finish()
    if len(mot.samples) > 30:
        step = len(mot.samples) / 30
        mot.samples = [mot.samples[int(k * step)] for k in range(30)]
obs = learned.load_observations(d / "observations.npz", mot)
calib, _ = learned.auto_calibrate(obs, mot.background())
pj = d / "play.json"
play = json.loads(pj.read_text()) if pj.exists() else None
hall = mot.background()
court = court_mask(calib) > 0
floor = cv2.cvtColor(hall, cv2.COLOR_BGR2LAB)[court].reshape(-1, 3).astype(np.float64).mean(axis=0)
frames = {fo.index: fo for fo in obs.frames}
# reference colours from every look of every frame on court (variant independent)
ref_looks = []
for fo in obs.frames[::4]:
    for t in fo.torsos:
        c = learned._torso_colour(t, floor)
        if c is not None:
            ref_looks.append(c)
ref = learn_kits(ref_looks, {})
H, A = _feature(ref["home"]), _feature(ref["away"])
kits = {}
if variant == "old":
    learned._learned_kits = lambda *a, **k: {}
elif variant.startswith("{"):
    kits = {k: hex_to_bgr(v) for k, v in json.loads(variant).items()}
    learned._learned_kits = lambda *a, **k: {}
st = {}
orig = pipeline.split_by_reading_colour


def spy(*a, **k):
    pts, s = orig(*a, **k)
    st.update(s)
    return pts, s


pipeline.split_by_reading_colour = spy
res = learned.track(obs, calib, kits, hall, play=play_intervals(play))
by = collections.defaultdict(list)
for p in res.points:
    if p.observed and p.det_index is not None and p.frame in frames:
        c = learned._torso_colour(frames[p.frame].torsos[p.det_index], floor)
        if c is not None:
            f = _feature(c)
            dh, da = np.linalg.norm(f - H), np.linalg.norm(f - A)
            if dh < 0.6 * da:
                by[p.track_id].append("h")
            elif da < 0.6 * dh:
                by[p.track_id].append("a")
mixed = 0
field = 0
minority_looks = 0
all_looks = 0
for t, s in by.items():
    if res.teams.get(t, {}).get("label") not in ("home", "away") or len(s) < 20:
        continue
    field += 1
    c = collections.Counter(s)
    m = min(c["h"], c["a"])
    minority_looks += m
    all_looks += len(s)
    if m >= 0.25 * len(s):
        mixed += 1
allp = collections.defaultdict(list)
for p in res.points:
    allp[p.track_id].append(p.frame)
dur = [(max(v) - min(v)) / res.fps for v in allp.values()]
print(
    json.dumps(
        {
            "variant": variant,
            "tracks": len(allp),
            "median_s": round(statistics.median(dur), 1),
            "field_tracks_20looks": field,
            "mixed": mixed,
            "minority_share": round(minority_looks / max(1, all_looks), 3),
            "reading_colour_pieces": st.get("pieces"),
            "kits_learned": res.extra.get("kits_learned"),
        }
    )
)

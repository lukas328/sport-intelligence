"""Random search of the tracker parameters with 2-fold cross-validation over the gold clips.

    PYTHONPATH=packages/vision python ml/gold/tune_tracker.py PRE_JSON [SEED] [N]
"""

import json, random, sys, dataclasses
sys.path.insert(0, "ml/gold")
from eval_ball import evaluate
from tracker import Params, track_clip
pre = json.load(open(sys.argv[1]))["clips"]
gold = json.load(open("ml/gold/data/gold_ball_v1.json"))
ids = sorted(gold["clips"]); A = set(ids[0::2]); B = set(ids[1::2])
rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 0)
space = dict(miss=[0.1,0.2,0.35,0.5,0.8], start=[0.5,1.2,2,3], w_net=[1,2,3,5], w_owl=[2,4,6,10],
  both=[0,0.4,1], net_min=[0.02,0.05,0.1], owl_min=[0.03,0.05,0.08], sigma0=[3,6,10],
  sigma_v=[0.2,0.35,0.6,1.0], sigma_new=[15,30,60], vmax=[50,70,100], gap=[2,4,6], static_frac=[0.3,0.5,0.8])
def run(p, clips):
    return evaluate(pre, gold, {"t": lambda c: track_clip(c, p)}, 12, clips)["t"]["all"]
res = []
cfgs = [Params()] + [Params(**{k: rnd.choice(v) for k, v in space.items()}) for _ in range(int(sys.argv[3]) if len(sys.argv)>3 else 120)]
for p in cfgs:
    res.append((run(p, A), run(p, B), p))
bA = max(res, key=lambda r: r[0]); bB = max(res, key=lambda r: r[1])
print("default A,B", res[0][:2])
print("best on A ->", round(bA[0],3), "test B", round(bA[1],3), bA[2])
print("best on B ->", round(bB[1],3), "test A", round(bB[0],3), bB[2])
res.sort(key=lambda r: -(r[0]+r[1]))
for r in res[:5]: print(round(r[0],3), round(r[1],3), {k: getattr(r[2],k) for k in space})

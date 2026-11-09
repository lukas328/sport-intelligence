"""Score the test crops with a trained model two ways: the classifier probability ("p", pred.json)
and, for models with the auxiliary ball heatmap, the heatmap peak inside the crop ("p" =
sigmoid of the max heatmap logit, pred_hm.json), plus their mean (pred_mix.json).

usage: score.py <data dir> <run dir>
"""

import json
import sys
from pathlib import Path

import numpy as np
import torch

D, R = Path(sys.argv[1]), Path(sys.argv[2])
ck = torch.load(R / "model.pt", map_location="cpu")
sys.argv = ["train.py", str(D), str(R / "_score"), "--ch", str(ck["ch"]), "--size", str(ck["w"]), "--aux", str(ck.get("aux", 0))]
import train as T  # noqa: E402  (parses the argv set above)

model = T.Net(ck["ch"], ck.get("aux", 0))
model.load_state_dict(ck["state"])
model.eval()
te = T.te
pc, ph = [], []
with torch.no_grad():
    for k in range(0, len(te), 64):
        logit, hm = model(T.batch(te[k : k + 64], False)[0])
        pc += torch.sigmoid(logit).tolist()
        if hm is not None:
            ph += torch.sigmoid(hm.flatten(1).max(1).values).tolist()
json.dump([{"file": m["file"], "p": round(p, 4)} for m, p in zip(te, pc)], open(R / "pred.json", "w"))
if ph:
    json.dump([{"file": m["file"], "p": round(p, 4)} for m, p in zip(te, ph)], open(R / "pred_hm.json", "w"))
    json.dump([{"file": m["file"], "p": round(float(np.sqrt(a * b)), 4)} for m, a, b in zip(te, pc, ph)], open(R / "pred_mix.json", "w"))
print("scored", len(te))

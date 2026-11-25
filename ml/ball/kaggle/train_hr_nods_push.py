"""Ball hr-nods (2026-11-25): BallHR from scratch on the hr1 data without DeepSport.

Every net from round 3 on trained with DeepSport (CC BY-NC-SA 4.0, research only), so none can
ship. This kernel is the hr1 kernel (pulled from Kaggle, `kaggle kernels pull
lukasde1000/handball-ball-hr1`, labels embedded) with the DeepSport dataset removed from the
sources (its pools stay empty and drop out of the mix) and its batch share moved to the own
labelled tiles (our_pos 30 -> 44, our_neg 16 -> 22). Same budget (9.5 h T4), same exclusions
(test set 2 games and halls). Compared against hr1 on ball test 2 (gold v2) once labelled.

    kaggle kernels pull lukasde1000/handball-ball-hr1 -p HR1 -m
    python ml/ball/kaggle/train_hr_nods_push.py HR1 WORKDIR   # then: kaggle kernels push -p WORKDIR
"""

import json
import sys
from pathlib import Path

hr1, work = Path(sys.argv[1]), Path(sys.argv[2])
work.mkdir(parents=True, exist_ok=True)
src = (hr1 / "handball-ball-hr1.py").read_text()
old = '"our_pos": 30, "ds_pos": 14,'
assert src.count(old) == 1, "mix anchor"
src = src.replace(old, '"our_pos": 44, "ds_pos": 0,')
old = '"our_neg": 16, "ds_neg": 6,'
assert src.count(old) == 1, "mix anchor"
src = src.replace(old, '"our_neg": 22, "ds_neg": 0,')
for a in ("ball_hr1.pt", "hr1_out.zip", "hr1_stats.json", "hr1_review_", "owl_tiles_hr1.zip"):
    src = src.replace(a, a.replace("hr1", "hrnods"))
src = '"""Ball hr-nods: hr1 without DeepSport (train_hr_nods_push.py)."""\n' + src
(work / "handball-ml-hr-nods.py").write_text(src)
meta = json.loads((hr1 / "kernel-metadata.json").read_text())
meta["dataset_sources"] = [d for d in meta["dataset_sources"] if "basketball" not in d]
meta.update(id="lukasde1000/handball-ml-hr-nods", title="handball ml hr nods", code_file="handball-ml-hr-nods.py")
meta.pop("id_no", None)
(work / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
print(work, "hr-nods kernel written")

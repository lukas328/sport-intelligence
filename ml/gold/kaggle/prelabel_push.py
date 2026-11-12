"""Build the Kaggle kernel of prelabel_gpu.py for the gold standard clips.

python ml/gold/kaggle/prelabel_push.py WORKDIR [--model ball_r8.pt]   # then: kaggle kernels push -p WORKDIR
"""

import argparse
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("work", type=Path)
ap.add_argument("--model", default="ball_r8.pt")
a = ap.parse_args()
clips = json.load(open(here.parent / "gold_clips.json"))["clips"]
a.work.mkdir(parents=True, exist_ok=True)
src = (
    (here / "prelabel_gpu.py")
    .read_text()
    .replace("__MODEL__", a.model)
    .replace("__CLIPS__", json.dumps(clips))
)
(a.work / "kaggle_gold_prelabel.py").write_text(src)
meta = {
    "id": "lukasde1000/handball-gold-prelabel",
    "title": "handball gold prelabel",
    "code_file": "kaggle_gold_prelabel.py",
    "language": "python",
    "kernel_type": "script",
    "is_private": True,
    "enable_gpu": True,
    "enable_internet": True,
    "dataset_sources": sorted(
        {f"lukasde1000/{c['dataset']}" for c in clips} | {"lukasde1000/handball-ball-models"}
    ),
    "competition_sources": [],
    "kernel_sources": [],
}
(a.work / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
print(a.work, len(clips), "clips", meta["dataset_sources"])

"""Build the Kaggle kernel of hardneg_gpu.py with the picks inserted.

    python ml/ball/kaggle/hardneg_push.py PICKS_JSON WORKDIR [--model ball_r7.pt] [--min-score 0.4]
        [--scene-w 640] [--id lukasde1000/handball-ball-hardneg]   # then: kaggle kernels push -p WORKDIR

Rounds 1 and 2 ran with the defaults; round 3: --model ball_r8.pt --min-score 0.2 --scene-w 1280.
"""
import argparse, json
from pathlib import Path

here = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("picks", type=Path); ap.add_argument("work", type=Path)
ap.add_argument("--model", default="ball_r7.pt"); ap.add_argument("--min-score", default="0.4")
ap.add_argument("--scene-w", default="640"); ap.add_argument("--id", default="lukasde1000/handball-ball-hardneg")
a = ap.parse_args()
picks = json.load(open(a.picks)); work = a.work; work.mkdir(parents=True, exist_ok=True)
src = (here / "hardneg_gpu.py").read_text()
for k, v in (("__MODEL__", a.model), ("__MIN_SCORE__", a.min_score), ("__SCENE_W__", a.scene_w), ("__PICKS__", json.dumps(picks))):
    src = src.replace(k, v)
(work / "kaggle_hardneg.py").write_text(src)
meta = {"id": a.id, "title": a.id.split("/")[1].replace("-", " "), "code_file": "kaggle_hardneg.py",
        "language": "python", "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": False,
        "dataset_sources": sorted({f"lukasde1000/{p['dataset']}" for p in picks} | {"lukasde1000/handball-ball-models"}),
        "competition_sources": [], "kernel_sources": []}
(work / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
print(work, len(picks), "picks", meta["dataset_sources"])

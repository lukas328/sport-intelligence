"""Round 10 of the 3-frame ball net: the round-9 recipe (train_r9_push.py) on all 171 training clips.

Labels from ml/gold/train_labels_r9.py over ml/gold/data/train_ball_v1.json exported with the
owner's review (tiers sure / track / confirmed: 5767 balls in 150 clips; the owner confirmed 2832
of Claude's 2902 unconfirmed fast points and rejected 55) plus the net's strongest wrong peak per
labelled frame as a hard negative. Starts from ball_r9.pt (kernel output of handball-ball-r9).

    python ml/ball/kaggle/train_r10_push.py LABELS_JSON WORKDIR   # then: kaggle kernels push -p WORKDIR
"""
import json, subprocess, sys
from pathlib import Path

here = Path(__file__).resolve().parent
work = Path(sys.argv[2]); work.mkdir(parents=True, exist_ok=True)
subprocess.run([sys.executable, str(here / "train_r9_push.py"), sys.argv[1], str(work)], check=True)
src = (work / "kaggle_r9.py").read_text()
for a, b in (("ball_r9.pt", "ball_r10.pt"), ("r9_out.zip", "r10_out.zip"), ("r9_stats.json", "r10_stats.json"),
             ("r9_review_", "r10_review_"), ("owl_tiles_r9.zip", "owl_tiles_r10.zip")):
    src = src.replace(a, b)
old = 'INIT = (glob.glob(INP + "/**/ball_r8.pt", recursive=True)'
assert src.count(old) == 1, "init anchor"
src = src.replace(old, 'INIT = (glob.glob(INP + "/**/ball_r9.pt", recursive=True) or glob.glob(INP + "/**/ball_r8.pt", recursive=True)')
src = src.replace('"""Round 9 (train_r9_push.py over round 8)', '"""Round 10 (train_r10_push.py over rounds 9 and 8)', 1)
(work / "kaggle_r9.py").unlink()
(work / "kaggle_r10.py").write_text(src)
meta = json.loads((work / "kernel-metadata.json").read_text())
meta.update(id="lukasde1000/handball-ball-r10", title="handball ball r10", code_file="kaggle_r10.py",
            kernel_sources=sorted(set(meta.get("kernel_sources", [])) | {"lukasde1000/handball-ball-r9"}))
(work / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
print(work, "round 10 kernel written")

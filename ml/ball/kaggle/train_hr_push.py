"""BallHR round 1: the HRNet-style net (ml/ball/ballhr.py) on exactly the data of round 10.

Same kernel as round 10 (train_r10_push.py over r9/r8/r7/r6: OWLv2 and mined tiles, DeepSport,
Roboflow, the owner's peaks, Claude's training clip labels with the owner's review), only the net
differs: BallHR instead of BallNet3, trained from scratch (no ImageNet, no earlier round), one
learning rate for all weights, a longer budget (more steps, since nothing is pre-trained).
So a gain on the gold standard is the architecture's, not the data's.

    python ml/ball/kaggle/train_hr_push.py LABELS_JSON WORKDIR   # then: kaggle kernels push -p WORKDIR
"""
import json, re, subprocess, sys
from pathlib import Path

here = Path(__file__).resolve().parent
work = Path(sys.argv[2]); work.mkdir(parents=True, exist_ok=True)
subprocess.run([sys.executable, str(here / "train_r10_push.py"), sys.argv[1], str(work)], check=True)
src = (work / "kaggle_r10.py").read_text()


def rep(old: str, new: str, count: int = 1) -> None:
    global src
    n = src.count(old)
    if n != count:
        raise SystemExit(f"patch anchor found {n} times (want {count}): {old[:70]!r}")
    src = src.replace(old, new)


for a, b in (("ball_r10.pt", "ball_hr1.pt"), ("r10_out.zip", "hr1_out.zip"), ("r10_stats.json", "hr1_stats.json"),
             ("r10_review_", "hr1_review_"), ("owl_tiles_r10.zip", "owl_tiles_hr1.zip")):
    src = src.replace(a, b)

# the net: BallHR from ml/ball/ballhr.py (module docstring and imports dropped, classes kept)
hr = (here.parent / "ballhr.py").read_text()
hr = hr[hr.index("def _bn"):]
rep("class BallNet3(nn.Module):", hr + "\n\nclass BallNet3(nn.Module):")
line = re.search(r"net = BallNet3\(\); net\.load_state_dict\(torch\.load\(INIT[^\n]*\n", src)
if not line:
    raise SystemExit("net anchor")
src = src.replace(line.group(0), "net = BallHR(); net.to(dev)  # from scratch\n")
rep('"lr": 1.5e-3}], weight_decay=1e-4)', '"lr": 1e-3}], weight_decay=1e-4)')
rep('ITERS = int(os.environ.get("ITERS", "30000"))', 'ITERS = int(os.environ.get("ITERS", "90000"))')
rep('BUDGET_S = float(os.environ.get("R6_BUDGET_H", "9.0"))', 'BUDGET_S = float(os.environ.get("R6_BUDGET_H", "9.5"))')
src = '"""BallHR round 1 (train_hr_push.py over round 10)."""\n' + src

(work / "kaggle_r10.py").unlink()
(work / "kaggle_hr1.py").write_text(src)
meta = json.loads((work / "kernel-metadata.json").read_text())
meta.update(id="lukasde1000/handball-ball-hr1", title="handball ball hr1", code_file="kaggle_hr1.py")
(work / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
print(work, "BallHR round 1 kernel written")

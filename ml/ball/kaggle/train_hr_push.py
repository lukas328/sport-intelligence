"""BallHR round 1: the HRNet-style net (ml/ball/ballhr.py) on exactly the data of round 10.

Same kernel as round 10 (train_r10_push.py over r9/r8/r7/r6: OWLv2 and mined tiles, DeepSport,
Roboflow, the owner's peaks, Claude's training clip labels with the owner's review), only the net
differs: BallHR instead of BallNet3, trained from scratch (no ImageNet, no earlier round), one
learning rate for all weights, a longer budget (more steps, since nothing is pre-trained).
So a gain on the gold standard is the architecture's, not the data's.

    python ml/ball/kaggle/train_hr_push.py LABELS_JSON WORKDIR [hrp]   # then: kaggle kernels push -p WORKDIR

With "hrp": BallHRP (ml/ball/ballhrp.py), timm's ImageNet-pretrained HRNet-W18, same data and
budget; the backbone learns at 3e-4, the new head at 1e-3. Kernel id handball-ball-hrp1.
"""
import json, re, subprocess, sys
from pathlib import Path

here = Path(__file__).resolve().parent
work = Path(sys.argv[2]); work.mkdir(parents=True, exist_ok=True)
PRE = len(sys.argv) > 3 and sys.argv[3] == "hrp"
TAG = "hrp1" if PRE else "hr1"
subprocess.run([sys.executable, str(here / "train_r10_push.py"), sys.argv[1], str(work)], check=True)
src = (work / "kaggle_r10.py").read_text()


def rep(old: str, new: str, count: int = 1) -> None:
    global src
    n = src.count(old)
    if n != count:
        raise SystemExit(f"patch anchor found {n} times (want {count}): {old[:70]!r}")
    src = src.replace(old, new)


for a, b in (("ball_r10.pt", f"ball_{TAG}.pt"), ("r10_out.zip", f"{TAG}_out.zip"), ("r10_stats.json", f"{TAG}_stats.json"),
             ("r10_review_", f"{TAG}_review_"), ("owl_tiles_r10.zip", f"owl_tiles_{TAG}.zip")):
    src = src.replace(a, b)

# the net: BallHR from ml/ball/ballhr.py (module docstring and imports dropped, classes kept)
if PRE:
    hr = (here.parent / "ballhrp.py").read_text()
    hr = "import timm\n" + hr[hr.index("class BallHRP"):]
else:
    hr = (here.parent / "ballhr.py").read_text()
    hr = hr[hr.index("def _bn"):]
rep("class BallNet3(nn.Module):", hr + "\n\nclass BallNet3(nn.Module):")
line = re.search(r"net = BallNet3\(\); net\.load_state_dict\(torch\.load\(INIT[^\n]*\n", src)
if not line:
    raise SystemExit("net anchor")
if PRE:
    src = src.replace(line.group(0), "net = BallHRP(); net.to(dev)  # ImageNet-pretrained HRNet-W18\n")
    rep('base = ("stem", "l1", "l2")', 'base = ("bb",)')
else:
    src = src.replace(line.group(0), "net = BallHR(); net.to(dev)  # from scratch\n")
rep('"lr": 1.5e-3}], weight_decay=1e-4)', '"lr": 1e-3}], weight_decay=1e-4)')
rep('ITERS = int(os.environ.get("ITERS", "30000"))', 'ITERS = int(os.environ.get("ITERS", "90000"))')
rep('BUDGET_S = float(os.environ.get("R6_BUDGET_H", "9.0"))', 'BUDGET_S = float(os.environ.get("R6_BUDGET_H", "9.5"))')
src = f'"""Ball {TAG} (train_hr_push.py over round 10)."""\n' + src

(work / "kaggle_r10.py").unlink()
(work / f"kaggle_{TAG}.py").write_text(src)
meta = json.loads((work / "kernel-metadata.json").read_text())
meta.update(id=f"lukasde1000/handball-ball-{TAG}", title=f"handball ball {TAG}", code_file=f"kaggle_{TAG}.py")
(work / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
print(work, TAG, "kernel written")

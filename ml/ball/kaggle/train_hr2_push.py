"""Second run of BallHR / BallHRP: continue from round 1 (hr1 / hrp1) on the same data.

Both round-1 nets were still improving when the 9.5 h budget ended (human validation 0.61 -> 0.63 and
0.67 -> 0.71 over the last checkpoints), and they had done fewer steps than BallNet3 (21 183 and
13 094; BallNet3 starts every round from the previous one). This run starts from ball_hr1.pt /
ball_hrp1.pt (kernel output of handball-ball-hr1 / -hrp1) with a fresh warm-up and cosine schedule
at half the learning rates; data and everything else as train_hr_push.py.

    python ml/ball/kaggle/train_hr2_push.py LABELS_JSON WORKDIR hr|hrp   # then: kaggle kernels push -p WORKDIR
"""
import json, subprocess, sys
from pathlib import Path

here = Path(__file__).resolve().parent
work = Path(sys.argv[2]); work.mkdir(parents=True, exist_ok=True)
PRE = sys.argv[3] == "hrp"
OLD, TAG = ("hrp1", "hrp2") if PRE else ("hr1", "hr2")
subprocess.run([sys.executable, str(here / "train_hr_push.py"), sys.argv[1], str(work)] + (["hrp"] if PRE else []), check=True)
src = (work / f"kaggle_{OLD}.py").read_text()


def rep(old: str, new: str) -> None:
    global src
    n = src.count(old)
    if n != 1:
        raise SystemExit(f"patch anchor found {n} times: {old[:70]!r}")
    src = src.replace(old, new)


for a in ("ball_{}.pt", "{}_out.zip", "{}_stats.json", "{}_review_", "owl_tiles_{}.zip"):
    src = src.replace(a.format(OLD), a.format(TAG))
load = (f'_I2 = glob.glob(INP + "/**/ball_{OLD}.pt", recursive=True)[0]; log("init", _I2)\n'
        '{net}; net.load_state_dict(torch.load(_I2, map_location="cpu", weights_only=True)); net.to(dev)\n')
if PRE:
    rep("net = BallHRP(); net.to(dev)  # ImageNet-pretrained HRNet-W18\n", load.format(net="net = BallHRP(pretrained=False)"))
else:
    rep("net = BallHR(); net.to(dev)  # from scratch\n", load.format(net="net = BallHR()"))
rep('"lr": 3e-4},', '"lr": 1.5e-4},')
rep('"lr": 1e-3}], weight_decay=1e-4)', '"lr": 5e-4}], weight_decay=1e-4)')
src = src.replace(f'"""Ball {OLD} (train_hr_push.py over round 10)."""', f'"""Ball {TAG} (train_hr2_push.py: {OLD} continued)."""', 1)

(work / f"kaggle_{OLD}.py").unlink()
(work / f"kaggle_{TAG}.py").write_text(src)
meta = json.loads((work / "kernel-metadata.json").read_text())
meta.update(id=f"lukasde1000/handball-ball-{TAG}", title=f"handball ball {TAG}", code_file=f"kaggle_{TAG}.py",
            kernel_sources=sorted(set(meta.get("kernel_sources", [])) | {f"lukasde1000/handball-ball-{OLD}"}))
(work / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
print(work, TAG, "kernel written")

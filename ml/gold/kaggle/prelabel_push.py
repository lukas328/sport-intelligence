"""Build the Kaggle kernel of prelabel_gpu.py for the gold standard clips.

python ml/gold/kaggle/prelabel_push.py WORKDIR [--model ball_r8.pt] [--arch ballhr]   # then: kaggle kernels push -p WORKDIR
"""

import argparse
import json
from pathlib import Path

here = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("work", type=Path)
ap.add_argument("--model", default="ball_r8.pt")
ap.add_argument("--clips", type=Path, default=here.parent / "gold_clips.json")
ap.add_argument("--id", default="lukasde1000/handball-gold-prelabel")
ap.add_argument("--arch", choices=("ballnet3", "ballhr", "ballhrp"), default="ballnet3", help="ballhr: ml/ball/ballhr.py")
a = ap.parse_args()
clips = json.load(open(a.clips))["clips"]
a.work.mkdir(parents=True, exist_ok=True)
src = (
    (here / "prelabel_gpu.py")
    .read_text()
    .replace("__MODEL__", a.model)
    .replace("__CLIPS__", json.dumps(clips))
)
if a.arch == "ballhr":  # the HRNet-style net (same input and output): inline its classes, build it
    hr = (here.parents[1] / "ball" / "ballhr.py").read_text()
    hr = hr[hr.index("def _bn") :]
    assert src.count("net = BallNet3()") == 1 and src.count("class BallNet3(nn.Module):") == 1
    src = src.replace("class BallNet3(nn.Module):", hr + "\n\nclass BallNet3(nn.Module):")
    src = src.replace("net = BallNet3()", "net = BallHR()")
if a.arch == "ballhrp":  # the ImageNet-pretrained HRNet-W18 net (timm); weights come from the model file
    hr = (here.parents[1] / "ball" / "ballhrp.py").read_text()
    hr = "import timm\n" + hr[hr.index("class BallHRP") :]
    assert src.count("net = BallNet3()") == 1 and src.count("class BallNet3(nn.Module):") == 1
    src = src.replace("class BallNet3(nn.Module):", hr + "\n\nclass BallNet3(nn.Module):")
    src = src.replace("net = BallNet3()", "net = BallHRP(pretrained=False)")
(a.work / "kaggle_gold_prelabel.py").write_text(src)
meta = {
    "id": a.id,
    "title": a.id.split("/")[1].replace("-", " "),
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

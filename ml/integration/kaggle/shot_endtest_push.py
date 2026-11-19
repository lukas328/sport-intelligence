"""Kaggle CPU kernels for the observe step of the shot test (`ml/integration/shot_segments_eval.py`):
the session's container is reclaimed while idle, so a run of many hours goes to Kaggle (free CPU,
4 cores, the segment datasets attached; no GPU). The marks stay local: scoring runs in the session.

    python ml/integration/kaggle/shot_endtest_push.py SEGMENTS.json WORK --models DIR --parts 4
    kaggle datasets create -p WORK/code     (or: datasets version -p WORK/code -m update)
    kaggle kernels push -p WORK/k0 ... WORK/k3

WORK/code: the vision and court packages, the two scripts and the models (yolox_s.onnx,
ball_hrp1.onnx) as one dataset; each kernel kN takes every Nth segment and runs observe in the CPU
test setting (hrp1 at 960 px on every 3rd frame) under Python 3.12 with the product's dependencies.
Result: /kaggle/working/out/<segment>/ (motion.npz, observations.npz, observe.json).
"""

from __future__ import annotations

import argparse
import json
import shutil
import tarfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OWNER = "lukasde1000"
CODE_SLUG = "handball-shot-endtest-code"

RUNNER = r"""
import json, os, shutil, subprocess, sys, tarfile
from pathlib import Path

SEGS = __SEGS__
inp = Path("/kaggle/input")
bundle = next(inp.rglob("bundle.tar"), None)
code = Path("/tmp/code")
if bundle is not None:
    with tarfile.open(bundle) as t:
        t.extractall(code, filter="data")
else:
    code = next(inp.rglob("shot_segments_eval.py")).parents[1]
models = next(inp.rglob("ball_hrp1.onnx")).parent
pip = ("pip install -q uv && uv python install 3.12 && uv venv -q -p 3.12 /tmp/v && "
       "VIRTUAL_ENV=/tmp/v uv pip install -q 'numpy>=2.1' 'opencv-python-headless>=4.10,<5' "
       "'scipy>=1.14' 'pyarrow>=18' 'av>=14' 'onnxruntime>=1.20' imageio-ffmpeg")
subprocess.run(pip, shell=True, check=True)
if shutil.which("ffmpeg") is None:
    exe = subprocess.check_output(["/tmp/v/bin/python", "-c",
        "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"], text=True).strip()
    os.makedirs("/tmp/bin", exist_ok=True)
    os.symlink(exe, "/tmp/bin/ffmpeg")
    os.environ["PATH"] = "/tmp/bin:" + os.environ["PATH"]
links = Path("/tmp/in")
for s in SEGS:
    src = next(inp.rglob(s["file"]))
    (links / s["dataset"]).mkdir(parents=True, exist_ok=True)
    dst = links / s["dataset"] / s["file"]
    if not dst.exists():
        dst.symlink_to(src)
Path("/tmp/segs.json").write_text(json.dumps(SEGS))
env = dict(os.environ, PYTHONPATH=f"{code}/vision:{code}/court:{code}/integration")
cmd = ["/tmp/v/bin/python", f"{code}/integration/shot_segments_eval.py", "observe", "/tmp/segs.json",
       "/kaggle/working/out", str(models), "--ball", str(models / "ball_hrp1.onnx"),
       "--width", "960", "--every", "3", "--input-root", str(links)]
subprocess.run(cmd, env=env, check=True)
"""


def _bundle(dst: Path) -> None:
    def skip(t: tarfile.TarInfo) -> tarfile.TarInfo | None:
        return None if "__pycache__" in t.name or "/tests" in t.name else t

    with tarfile.open(dst, "w") as t:
        t.add(REPO / "packages/vision/handball_vision", "vision/handball_vision", filter=skip)
        court = REPO / "packages/court"
        t.add(court / "handball_court", "court/handball_court", filter=skip)
        t.add(court / "generated", "court/generated", filter=skip)
        t.add(court / "spec", "court/spec", filter=skip)
        for f in ("shot_segments_eval.py", "profile_analysis.py"):
            t.add(REPO / "ml/integration" / f, f"integration/{f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("segments", type=Path)
    ap.add_argument("work", type=Path)
    ap.add_argument("--models", type=Path, required=True, help="yolox_s.onnx, ball_hrp1.onnx")
    ap.add_argument("--parts", type=int, default=4)
    ap.add_argument("--tag", default="shot-endtest")
    a = ap.parse_args()
    segs = json.loads(a.segments.read_text())
    code = a.work / "code"
    code.mkdir(parents=True, exist_ok=True)
    _bundle(code / "bundle.tar")
    for m in ("yolox_s.onnx", "ball_hrp1.onnx"):
        shutil.copy2(a.models / m, code / m)
    (code / "dataset-metadata.json").write_text(
        json.dumps(
            {
                "title": CODE_SLUG.replace("-", " "),
                "id": f"{OWNER}/{CODE_SLUG}",
                "licenses": [{"name": "other"}],
            }
        )
    )
    for k in range(a.parts):
        part = segs[k :: a.parts]
        kd = a.work / f"k{k}"
        kd.mkdir(parents=True, exist_ok=True)
        (kd / "run.py").write_text(RUNNER.replace("__SEGS__", json.dumps(part)))
        meta = {
            "id": f"{OWNER}/handball-{a.tag}-{k}",
            "title": f"handball {a.tag} {k}",
            "code_file": "run.py",
            "language": "python",
            "kernel_type": "script",
            "is_private": True,
            "enable_gpu": False,
            "enable_internet": True,
            "dataset_sources": sorted(
                {f"{OWNER}/{s['dataset']}" for s in part} | {f"{OWNER}/{CODE_SLUG}"}
            ),
            "competition_sources": [],
            "kernel_sources": [],
        }
        (kd / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
        print(kd, len(part), "segments")


if __name__ == "__main__":
    main()

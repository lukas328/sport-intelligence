"""Ball pre-labels for a clip list on Modal: the gold prelabel kernel (ml/gold/kaggle/prelabel_gpu.py)
once per ball net, OWLv2 only in the first run. The result goes to Kaggle as
handball-gpu-prelabel-<tag>-<date>: clips/<id>.mp4 (from the first run) and <net>/pre.json per net.

usage: modal run --detach ml/gpu/prelabel_clips.py [--clips ml/gold/shot_clips.json] [--tag shots]
       [--nets hrp2:ballhrp,hr2:ballhr,hrp1:ballhrp,hr1:ballhr] [--gpu T4]

Nets come from the Kaggle dataset handball-ball-hrmodels (ball_<net>.pt); arch ballnet3, ballhr
or ballhrp as in prelabel_push.py. Cost for the 61 shot clips (about 32 000 frames): OWLv2 on every
2nd frame about 2.5 h, each net about 0.5 h, so about 4.5 h on a T4, roughly 3 USD.
"""

from __future__ import annotations

import datetime as dt
import json

import modal

from common import REPO, base_image, kaggle_download, kaggle_publish, kaggle_secret

app = modal.App("handball-prelabel")
out_vol = modal.Volume.from_name("handball-gpu-out", create_if_missing=True)
image = (
    base_image.pip_install("timm==1.0.11")
    .add_local_python_source("common")
    .add_local_file(str(REPO / "ml/gold/kaggle/prelabel_gpu.py"), "/root/prelabel_gpu.py")
    .add_local_file(str(REPO / "ml/ball/ballhr.py"), "/root/ballhr.py")
    .add_local_file(str(REPO / "ml/ball/ballhrp.py"), "/root/ballhrp.py")
)


def _kernel(clips: list, model: str, arch: str, owl: bool, inp: str, out: str) -> str:
    """prelabel_gpu.py with its placeholders filled, as prelabel_push.py builds it for Kaggle."""
    from pathlib import Path

    src = Path("/root/prelabel_gpu.py").read_text()
    src = src.replace("__MODEL__", model).replace("__CLIPS__", json.dumps(clips))
    src = src.replace('IN = "/kaggle/input"', f'IN = "{inp}"').replace('OUT = "/kaggle/working"', f'OUT = "{out}"')
    if not owl:
        assert src.count("OWL_EVERY = 2") == 1
        src = src.replace("OWL_EVERY = 2", "OWL_EVERY = 10**9")
    if arch in ("ballhr", "ballhrp"):
        name = "ballhr.py" if arch == "ballhr" else "ballhrp.py"
        hr = Path(f"/root/{name}").read_text()
        hr = hr[hr.index("def _bn"):] if arch == "ballhr" else "import timm\n" + hr[hr.index("class BallHRP"):]
        assert src.count("net = BallNet3()") == 1 and src.count("class BallNet3(nn.Module):") == 1
        src = src.replace("class BallNet3(nn.Module):", hr + "\n\nclass BallNet3(nn.Module):")
        src = src.replace("net = BallNet3()", "net = BallHR()" if arch == "ballhr" else "net = BallHRP(pretrained=False)")
    return src


def _run(clips_json: str, nets: str, slug: str) -> str:
    import shutil
    import subprocess
    from pathlib import Path

    clips = json.loads(clips_json)["clips"]
    inp, out = Path("/tmp/in"), Path("/vol") / slug
    kaggle_download(sorted({c["dataset"] for c in clips}) + ["handball-ball-hrmodels"], inp)
    for i, spec in enumerate(n for n in nets.split(",") if n):
        net, arch = spec.split(":")
        work = Path("/tmp/work") / net
        work.mkdir(parents=True, exist_ok=True)
        (work / "k.py").write_text(_kernel(clips, f"ball_{net}.pt", arch, i == 0, str(inp), str(work)))
        print("run", net, arch, "owl" if i == 0 else "", flush=True)
        subprocess.run(["python", str(work / "k.py")], check=True)
        (out / net).mkdir(parents=True, exist_ok=True)
        shutil.copy2(work / "pre.json", out / net / "pre.json")
        if i == 0:
            shutil.copytree(work / "clips", out / "clips", dirs_exist_ok=True)
        out_vol.commit()
    return kaggle_publish(out, slug)


@app.function(gpu="T4", image=image, secrets=[kaggle_secret], timeout=12 * 3600, volumes={"/vol": out_vol})
def run_t4(clips_json: str, nets: str, slug: str) -> str:
    return _run(clips_json, nets, slug)


@app.function(gpu="L4", image=image, secrets=[kaggle_secret], timeout=12 * 3600, volumes={"/vol": out_vol})
def run_l4(clips_json: str, nets: str, slug: str) -> str:
    return _run(clips_json, nets, slug)


@app.local_entrypoint()
def main(clips: str = "ml/gold/shot_clips.json", tag: str = "shots",
         nets: str = "hrp2:ballhrp,hr2:ballhr,hrp1:ballhrp,hr1:ballhr", gpu: str = "T4") -> None:
    slug = f"handball-gpu-prelabel-{tag}-{dt.datetime.now(dt.timezone.utc):%Y%m%d-%H%M}"
    fn = run_l4 if gpu.upper() == "L4" else run_t4
    print("result dataset:", fn.remote((REPO / clips).read_text(), nets, slug))

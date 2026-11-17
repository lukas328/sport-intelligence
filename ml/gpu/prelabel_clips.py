"""Ball pre-labels for a clip list on Modal: the gold prelabel kernel (ml/gold/kaggle/prelabel_gpu.py)
once per ball net, OWLv2 only in the first net's run. The result goes to Kaggle as
handball-gpu-prelabel-<tag>: clips/<id>.mp4 (from the first net) and <net>/pre.json per net.

usage: modal run --detach ml/gpu/prelabel_clips.py [--clips ml/gold/shot_clips.json] [--tag shots]
       [--nets hrp1:ballhrp,hr1:ballhr] [--owl-every 4] [--chunk 5] [--gpu T4]

Resumable: Modal may take the GPU back (preemption) and restart the function from the start. The
clips are therefore done in chunks of --chunk clips; each finished chunk is written to the volume
handball-gpu-out under the slug (`<net>/part_NN.json`, the clips' mp4s) and committed, and a restart
skips every chunk that is already there. The slug is fixed by --tag (no date), so running the same
command again also continues. Only after all chunks of all nets the parts are merged into
`<net>/pre.json` and published to Kaggle.

Nets come from the Kaggle dataset handball-ball-hrmodels (ball_<net>.pt); arch ballnet3, ballhr or
ballhrp as in prelabel_push.py. Cost for the 61 shot clips (about 32 000 frames), measured on the
first attempt (2026-11-16): OWLv2 is the bulk, about 1.4 s per frame it runs on; with --owl-every 4
about 8 000 frames, so about 3 h, plus about 0.3 h per net: about 3.5 h on a T4, roughly 2.5 USD.
"""

from __future__ import annotations

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


def _kernel(clips: list, model: str, arch: str, owl_every: int, inp: str, out: str) -> str:
    """prelabel_gpu.py with its placeholders filled, as prelabel_push.py builds it for Kaggle."""
    from pathlib import Path

    src = Path("/root/prelabel_gpu.py").read_text()
    src = src.replace("__MODEL__", model).replace("__CLIPS__", json.dumps(clips))
    src = src.replace('IN = "/kaggle/input"', f'IN = "{inp}"').replace('OUT = "/kaggle/working"', f'OUT = "{out}"')
    assert src.count("OWL_EVERY = 2") == 1
    src = src.replace("OWL_EVERY = 2", f"OWL_EVERY = {owl_every if owl_every > 0 else 10**9}")
    if arch in ("ballhr", "ballhrp"):
        name = "ballhr.py" if arch == "ballhr" else "ballhrp.py"
        hr = Path(f"/root/{name}").read_text()
        hr = hr[hr.index("def _bn"):] if arch == "ballhr" else "import timm\n" + hr[hr.index("class BallHRP"):]
        assert src.count("net = BallNet3()") == 1 and src.count("class BallNet3(nn.Module):") == 1
        src = src.replace("class BallNet3(nn.Module):", hr + "\n\nclass BallNet3(nn.Module):")
        src = src.replace("net = BallNet3()", "net = BallHR()" if arch == "ballhr" else "net = BallHRP(pretrained=False)")
    return src


def _run(clips_json: str, nets: str, slug: str, owl_every: int, chunk: int) -> str:
    import shutil
    import subprocess
    from pathlib import Path

    clips = json.loads(clips_json)["clips"]
    inp, out = Path("/tmp/in"), Path("/vol") / slug
    specs = [n.split(":") for n in nets.split(",") if n]
    parts = [clips[i:i + chunk] for i in range(0, len(clips), chunk)]
    todo = [(i, net) for net, _ in specs for i in range(len(parts)) if not (out / net / f"part_{i:02d}.json").exists()]
    print(f"{len(parts)} chunks x {len(specs)} nets, {len(todo)} still to do", flush=True)
    if todo:
        kaggle_download(sorted({c["dataset"] for c in clips}) + ["handball-ball-hrmodels"], inp)
    for k, (net, arch) in enumerate(specs):
        for i, part in enumerate(parts):
            dst = out / net / f"part_{i:02d}.json"
            if dst.exists():
                continue
            work = Path("/tmp/work") / net / f"{i:02d}"
            shutil.rmtree(work, ignore_errors=True)
            work.mkdir(parents=True)
            (work / "k.py").write_text(_kernel(part, f"ball_{net}.pt", arch, owl_every if k == 0 else 0, str(inp), str(work)))
            print("run", net, "chunk", i, [c["id"] for c in part], flush=True)
            subprocess.run(["python", str(work / "k.py")], check=True)
            if k == 0:
                shutil.copytree(work / "clips", out / "clips", dirs_exist_ok=True)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(work / "pre.json", dst)  # last: a chunk counts as done only once its part is there
            out_vol.commit()
    for net, _ in specs:  # merge the parts
        merged: dict = {}
        for i in range(len(parts)):
            d = json.loads((out / net / f"part_{i:02d}.json").read_text())
            merged.setdefault("model", d["model"])
            merged.setdefault("owl_every", d["owl_every"])
            merged.setdefault("clips", {}).update(d["clips"])
        (out / net / "pre.json").write_text(json.dumps(merged))
    out_vol.commit()
    return kaggle_publish(out, slug)


@app.function(gpu="T4", image=image, secrets=[kaggle_secret], timeout=12 * 3600, volumes={"/vol": out_vol})
def run_t4(clips_json: str, nets: str, slug: str, owl_every: int, chunk: int) -> str:
    return _run(clips_json, nets, slug, owl_every, chunk)


@app.function(gpu="L4", image=image, secrets=[kaggle_secret], timeout=12 * 3600, volumes={"/vol": out_vol})
def run_l4(clips_json: str, nets: str, slug: str, owl_every: int, chunk: int) -> str:
    return _run(clips_json, nets, slug, owl_every, chunk)


@app.local_entrypoint()
def main(clips: str = "ml/gold/shot_clips.json", tag: str = "shots", nets: str = "hrp1:ballhrp,hr1:ballhr",
         owl_every: int = 4, chunk: int = 5, gpu: str = "T4") -> None:
    slug = f"handball-gpu-prelabel-{tag}"
    fn = run_l4 if gpu.upper() == "L4" else run_t4
    print("result dataset:", fn.remote((REPO / clips).read_text(), nets, slug, owl_every, chunk))

"""Smoke test for the Modal setup: GPU visible, Kaggle secret works, a small dataset downloads.
Uploads nothing.  usage: modal run ml/gpu/smoke.py"""

from __future__ import annotations

import modal

from common import base_image, kaggle_download, kaggle_secret

app = modal.App("handball-smoke")
image = base_image.add_local_python_source("common")


@app.function(gpu="T4", image=image, secrets=[kaggle_secret], timeout=900)
def smoke() -> dict:
    import subprocess
    from pathlib import Path

    import torch

    info = {
        "cuda": torch.cuda.is_available(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }
    root = Path("/tmp/in")
    kaggle_download(["handball-ball-models"], root)
    info["files"] = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())[:10]
    info["nvidia_smi"] = subprocess.run(
        ["nvidia-smi", "-L"], capture_output=True, text=True
    ).stdout.strip()
    return info


@app.local_entrypoint()
def main() -> None:
    print(smoke.remote())

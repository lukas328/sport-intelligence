"""Shared pieces of the Modal GPU jobs: the container image and the Kaggle in/out helpers.

The jobs run on Modal from the owner's computer (docs/plans/gpu-jobs-local.md). Inputs come from
private Kaggle datasets, results go back as a new private Kaggle dataset, so the cloud session can
pick them up. Kaggle credentials come from the Modal secret "kaggle" (KAGGLE_USERNAME, KAGGLE_KEY).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import modal

REPO = Path(__file__).resolve().parents[2]

base_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install(
        "torch==2.5.1",
        "torchvision==0.20.1",
        "transformers==4.46.3",
        "opencv-python-headless==4.10.0.84",
        "numpy<2",
        "kaggle==1.6.17",
        "onnx==1.17.0",
    )
)
kaggle_secret = modal.Secret.from_name("kaggle")


def kaggle_download(datasets: list[str], root: Path) -> None:
    """Each dataset (owner/slug or slug) into root/<slug>, unzipped."""
    user = os.environ["KAGGLE_USERNAME"]
    for d in datasets:
        ref = d if "/" in d else f"{user}/{d}"
        dest = root / ref.split("/")[1]
        dest.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["kaggle", "datasets", "download", "-d", ref, "-p", str(dest), "--unzip", "-q"],
            check=True,
        )


def kaggle_publish(folder: Path, slug: str, title: str | None = None) -> str:
    """folder as a new private dataset owner/slug (zipped into one archive to keep uploads fast)."""
    user = os.environ["KAGGLE_USERNAME"]
    pack = folder.parent / f"{slug}_pack"
    pack.mkdir(exist_ok=True)
    shutil.make_archive(str(pack / "result"), "zip", folder)
    (pack / "dataset-metadata.json").write_text(
        json.dumps(
            {"title": title or slug, "id": f"{user}/{slug}", "licenses": [{"name": "other"}]}
        )
    )
    res = subprocess.run(
        ["kaggle", "datasets", "create", "-p", str(pack)], capture_output=True, text=True
    )
    out = (res.stdout + res.stderr).strip()
    print(out, flush=True)
    if res.returncode:
        raise RuntimeError(f"kaggle upload failed: {out[-300:]}")
    return f"{user}/{slug}"

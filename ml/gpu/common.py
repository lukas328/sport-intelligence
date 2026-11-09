"""Shared pieces of the Modal GPU jobs: the container image and the Kaggle in/out helpers.

The jobs run on Modal from the owner's computer (docs/plans/gpu-jobs-local.md). Inputs come from
private Kaggle datasets, results go back as a new private Kaggle dataset, so the cloud session can
pick them up. Kaggle credentials come from the Modal secret "kaggle": KAGGLE_API_TOKEN (new-style token, the
content of ~/.kaggle/access_token) or the legacy KAGGLE_USERNAME + KAGGLE_KEY.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import modal

# Repo root on the owner's computer; inside the container common.py sits in /root, without parents.
_here = Path(__file__).resolve()
REPO = _here.parents[2] if len(_here.parents) > 2 else _here.parent

base_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install(
        "torch==2.5.1",
        "torchvision==0.20.1",
        "transformers==4.46.3",
        "opencv-python-headless==4.10.0.84",
        "numpy<2",
        "kaggle==2.2.5",
        "six",
        "kagglesdk==0.1.38",
        "onnx==1.17.0",
    )
)
kaggle_secret = modal.Secret.from_name("kaggle")
KAGGLE_OWNER = "lukasde1000"


def kaggle_download(datasets: list[str], root: Path) -> None:
    """Each dataset (owner/slug or slug) into root/<slug>, unzipped."""
    user = os.environ.get("KAGGLE_USERNAME", KAGGLE_OWNER)
    for d in datasets:
        ref = d if "/" in d else f"{user}/{d}"
        dest = root / ref.split("/")[1]
        dest.mkdir(parents=True, exist_ok=True)
        res = subprocess.run(
            ["kaggle", "datasets", "download", "-d", ref, "-p", str(dest), "--unzip", "-q"]
        )
        if res.returncode:
            # Kaggle sometimes builds no archive for a dataset (size 0 in the listing, e.g.
            # handball-ball-models); the whole download is then a 404, single files still work.
            print(f"{ref}: whole download failed, falling back to file by file", flush=True)
            _download_file_by_file(ref, dest)


def _download_file_by_file(ref: str, dest: Path) -> None:
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    token = None
    while True:
        page = api.dataset_list_files(ref, page_token=token, page_size=200)
        for f in page.files:
            api.dataset_download_file(ref, f.name, path=str(dest), quiet=True)
        token = page.next_page_token
        if not token:
            break


def kaggle_publish(folder: Path, slug: str, title: str | None = None) -> str:
    """folder as a new private dataset owner/slug (zipped into one archive to keep uploads fast)."""
    user = os.environ.get("KAGGLE_USERNAME", KAGGLE_OWNER)
    pack = Path("/tmp") / f"{slug}_pack"
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

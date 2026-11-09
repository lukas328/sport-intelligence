"""Every background job the API queues names a function that exists in the worker code.

The API queues jobs by dotted path (no import, the workers are separate apps), so a moved function
fails silently at runtime: reels were never rendered because the path still pointed at
handball_worker.export after the function moved to handball_worker.reels."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
API = ROOT / "apps" / "api" / "src"
WORKERS = {
    "handball_worker": ROOT / "apps" / "worker" / "src" / "handball_worker",
    "handball_gpu_worker": ROOT / "apps" / "gpu-worker" / "src" / "handball_gpu_worker",
}


def test_queued_job_paths_exist() -> None:
    paths = set()
    for f in API.rglob("*.py"):
        paths |= set(
            re.findall(r'"((?:handball_worker|handball_gpu_worker)(?:\.\w+)+)"', f.read_text())
        )
    assert paths, "no job paths found"
    for path in sorted(paths):
        package, *modules, func = path.split(".")
        source = WORKERS[package].joinpath(*modules).with_suffix(".py")
        assert source.exists(), f"{path}: no module {source}"
        assert re.search(rf"^def {func}\(", source.read_text(), re.M), f"{path}: no function {func}"

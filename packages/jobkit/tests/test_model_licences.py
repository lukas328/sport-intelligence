"""Licence check of the shipped models and packages (ADR 003, docs/plans/lizenzen-modelle.md).

Every model file named in the images, the job settings, infra or the workflows must be in the
register `infra/model-licences.json`; a model that may not reach a paying club ("test-only")
may appear in infra only where the register lists that use with its open question, and every
such listed use must still exist (removing it from infra means removing it from the list). No
package of the product lockfile may be on the register's forbidden list (AGPL detectors and
trackers)."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGISTER = json.loads((ROOT / "infra" / "model-licences.json").read_text(encoding="utf-8"))
MODEL = re.compile(r"(?<![\w.-])(/?models/[A-Za-z0-9_./-]+\.onnx)")
SCANNED = [
    *sorted((ROOT / "apps").glob("*/Dockerfile*")),
    ROOT / "packages" / "jobkit" / "handball_jobkit" / "settings.py",
    *sorted(
        p
        for p in (ROOT / "infra").rglob("*")
        if p.is_file()
        and p.suffix in {".tf", ".json", ".yml", ".yaml", ".hcl", ".sh", ".env", ".example"}
        and p.name != "model-licences.json"
    ),
    *sorted((ROOT / ".github" / "workflows").glob("*.yml")),
]


def _uses() -> dict[str, set[str]]:
    """Model file -> the files (relative to the repository) that name it."""
    out: dict[str, set[str]] = {}
    for path in SCANNED:
        for name in MODEL.findall(path.read_text(encoding="utf-8", errors="replace")):
            out.setdefault(name, set()).add(path.relative_to(ROOT).as_posix())
    return out


def test_every_model_the_product_names_is_in_the_register() -> None:
    unknown = {m: sorted(f) for m, f in _uses().items() if m not in REGISTER["models"]}
    assert not unknown, (
        f"models without a licence entry in infra/model-licences.json: {unknown}. Add the model "
        "with its licence and status (docs/plans/lizenzen-modelle.md) before it is used."
    )
    for name, entry in REGISTER["models"].items():
        assert entry["status"] in ("shippable", "test-only"), name
        assert entry["licence"] and entry["source"], name


def test_test_only_models_appear_in_infra_only_where_listed() -> None:
    listed = {
        (file, model)
        for file, models in REGISTER["test_only_in_infra"].items()
        if not file.startswith("_")
        for model in models
    }
    found = {
        (file, model)
        for model, files in _uses().items()
        if REGISTER["models"].get(model, {}).get("status") == "test-only"
        for file in files
        if file.startswith("infra/") or file.startswith(".github/")
    }
    new = sorted(found - listed)
    assert not new, (
        f"test-only models (no commercial licence) set in infra: {new}. Use a shippable model, "
        "or list the use with its open question in infra/model-licences.json."
    )
    stale = sorted(listed - found)
    assert not stale, (
        f"listed test-only uses no longer in infra, remove them from the list: {stale}"
    )


def test_the_lockfile_has_no_forbidden_package() -> None:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    names = {str(p["name"]).lower() for p in lock.get("package", [])}
    hits = {n: why for n, why in REGISTER["forbidden_packages"].items() if n in names}
    assert not hits, f"forbidden packages in uv.lock: {hits}"


def test_the_check_finds_models_and_forbidden_packages() -> None:
    """The scanner itself: model names in quotes, paths and variables are found; unrelated text
    is not."""
    text = 'HB_BALL_MODEL = "models/ball/x-1.onnx"\nopen("/models/yolox_s.onnx")\nmymodels/y.onnx'
    assert MODEL.findall(text) == ["models/ball/x-1.onnx", "/models/yolox_s.onnx"]
    assert {"ultralytics", "boxmot"} <= set(REGISTER["forbidden_packages"])

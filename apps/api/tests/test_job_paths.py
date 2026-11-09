"""Every background job the API queues names a function that exists in the worker code, and the
payload the API sends fits that function.

The API queues jobs by dotted path (no import, the workers are separate apps), so a moved function
fails silently at runtime: reels were never rendered because the path still pointed at
handball_worker.export after the function moved to handball_worker.reels. The same goes for a
renamed parameter or payload key: RQ calls the function with the API's keyword arguments.

The worker sources are read with `ast` (not imported), the payloads are the ones the API really
queues in the flows below (memory job queue)."""

from __future__ import annotations

import ast
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from handball_api.core.jobs import MemoryJobQueue

from .conftest import Api, setup_club
from .test_identity_sync import _finish, _ingest, _tracks
from .test_matches import new_match, upload

ROOT = Path(__file__).resolve().parents[3]
API = ROOT / "apps" / "api" / "src"
WORKERS = {
    "handball_worker": ROOT / "apps" / "worker" / "src" / "handball_worker",
    "handball_gpu_worker": ROOT / "apps" / "gpu-worker" / "src" / "handball_gpu_worker",
}


def queued_paths() -> set[str]:
    paths: set[str] = set()
    for f in API.rglob("*.py"):
        paths |= set(
            re.findall(r'"((?:handball_worker|handball_gpu_worker)(?:\.\w+)+)"', f.read_text())
        )
    return paths


def module_of(path: str) -> Path:
    package, *modules, _ = path.split(".")
    return WORKERS[package].joinpath(*modules).with_suffix(".py")


@dataclass(frozen=True)
class Signature:
    params: set[str]
    required: set[str]
    var_keyword: bool
    payload_keys: set[str]  # payload["key"] read in the module (for jobs taking one payload dict)


def signature(path: str) -> Signature:
    tree = ast.parse(module_of(path).read_text())
    func = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == path.rsplit(".", 1)[1]
    )
    args = func.args
    positional = args.posonlyargs + args.args
    with_default = {a.arg for a in positional[len(positional) - len(args.defaults) :]}
    with_default |= {a.arg for a, d in zip(args.kwonlyargs, args.kw_defaults, strict=True) if d}
    params = {a.arg for a in positional + args.kwonlyargs}
    keys = {
        n.slice.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Subscript)
        and isinstance(n.value, ast.Name)
        and n.value.id == "payload"
        and isinstance(n.slice, ast.Constant)
        and isinstance(n.slice.value, str)
    }
    return Signature(params, params - with_default, args.kwarg is not None, keys)


def check_call(path: str, kwargs: dict[str, Any]) -> None:
    sig = signature(path)
    sent = set(kwargs)
    if not sig.var_keyword:
        assert sent <= sig.params, f"{path}: unknown parameters {sorted(sent - sig.params)}"
    assert sig.required <= sent, f"{path}: missing parameters {sorted(sig.required - sent)}"
    if "payload" in sig.params:
        missing = sig.payload_keys - set(kwargs["payload"])
        assert not missing, f"{path}: payload lacks {sorted(missing)}"


def test_queued_job_paths_exist() -> None:
    paths = queued_paths()
    assert paths, "no job paths found"
    for path in sorted(paths):
        func = path.rsplit(".", 1)[1]
        source = module_of(path)
        assert source.exists(), f"{path}: no module {source}"
        assert re.search(rf"^def {func}\(", source.read_text(), re.M), f"{path}: no function {func}"


def test_check_call_catches_drift() -> None:
    ingest = "handball_worker.ingest.run_ingest"
    good = dict.fromkeys(
        ("job_id", "organization_id", "match_id", "asset_id", "bucket", "key", "prefix"), "x"
    )
    check_call(ingest, good)
    with pytest.raises(AssertionError, match="unknown parameters"):
        check_call(ingest, {**good, "url": "x"})
    with pytest.raises(AssertionError, match="missing parameters"):
        check_call(ingest, {k: v for k, v in good.items() if k != "prefix"})
    with pytest.raises(AssertionError, match="payload lacks"):
        check_call("handball_worker.push.send", {"payload": {"tokens": []}})
    # run_sync takes **kwargs: extra keys are fine
    sync = {"job_id": "j", "bucket": "b", "main_audio_key": "a", "other_audio_key": "o"}
    check_call("handball_gpu_worker.sync.run_sync", {**sync, "organization_id": "x"})


@pytest.mark.usefixtures("clean_db")
async def test_payloads_fit_the_worker_functions(
    make_api: Callable[[], Api], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Runs every flow that queues a job once and checks each queued call against the worker."""
    api = make_api()
    ids = await setup_club(api)
    org, team = ids["org"], ids["team"]
    jobs: MemoryJobQueue = api.app.state.jobs
    roster = f"/v1/orgs/{org}/teams/{team}/seasons/{ids['season']}/roster"
    lena = (
        await api.post(roster, json={"first_name": "Lena", "last_name": "M", "jersey_number": 7})
    ).json()
    r = await api.post(
        f"/v1/orgs/{org}/teams/{team}/players/{lena['player_id']}/consents",
        json={
            "kind": "highlights_internal",
            "given_by": "self",
            "given_by_name": "X",
            "given_at": "2026-10-01T10:00:00+02:00",
        },
    )
    assert r.status_code == 201, r.text
    devices = await api.post(
        "/v1/me/devices", json={"token": "ExponentPushToken[contract]", "platform": "ios"}
    )
    assert devices.status_code == 204
    m = await new_match(api, ids)
    for i in range(3):
        await api.post(
            f"/v1/orgs/{org}/matches/{m['id']}/events",
            json={
                "type": "shot",
                "side": "own",
                "outcome": "goal",
                "t_ms": 30_000 * (i + 1),
                "player_id": lena["player_id"],
            },
        )

    # ingest of a second camera, then the main video: analysis and camera sync
    await upload(api, ids, m["id"], b"g" * 100, name="tor.mp4", role="goal_cam_left")
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    await upload(api, ids, m["id"], b"v" * 100)
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    analysis = next(j for j in reversed(jobs.jobs) if j[1].endswith(".run_analysis"))
    # the analysis result: highlight reels and an "analysis ready" push
    await _finish(api, analysis[2], {"tracks": _tracks(), "detector": "heuristic"})

    # link import
    import handball_api.services.videos as videos

    monkeypatch.setattr(videos, "check_public_https_url", lambda u: u)
    r = await api.post(
        f"/v1/orgs/{org}/matches/{m['id']}/videos/import",
        json={"url": "https://cdn.example.com/game.mp4"},
    )
    assert r.status_code == 202, r.text

    # presentation export (a text slide is enough)
    pres = (
        await api.post(
            f"/v1/orgs/{org}/teams/{team}/presentations", json={"title": "T", "match_id": m["id"]}
        )
    ).json()
    base = f"/v1/orgs/{org}/presentations/{pres['id']}"
    await api.post(f"{base}/slides", json={"type": "text", "content": {"title": "Rückzug"}})
    assert (await api.post(f"{base}/export")).status_code == 202

    seen = {func for _, func, _, _ in jobs.jobs}
    assert seen == queued_paths(), f"flows do not cover {sorted(queued_paths() - seen)}"
    for _, func, _, kwargs in jobs.jobs:
        check_call(func, kwargs)

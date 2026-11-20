"""Keep the free Kaggle CPU busy: a fixed queue of segments, observed in long kernels (the product
observe step in the CPU test setting, as `shot_endtest_push.py`), refilled whenever a slot is free.

Kaggle runs at most MAX_SLOTS batch CPU sessions at once, each up to 12 h. A batch holds BATCH
segments (20 to 50 min of CPU each, depending on the machine; see BATCH), and batch i always runs as
kernel `handball-obs-qNNN`, so the queue file alone says what is done: any session can continue.

    python ml/integration/kaggle/observe_queue.py build LIBRARY_DIR     # writes the queue file
    python ml/integration/kaggle/observe_queue.py step                  # push into free slots
    python ml/integration/kaggle/observe_queue.py status

Order of the queue: the rest of the dev games (segments with an official log, the pauses between
them), then every other game of the library. The end-test games are never queued (no design work
may look at other segments of those halls). Result per kernel: /kaggle/working/out/<segment>/
(motion.npz, observations.npz, observe.json); `kaggle kernels output` fetches it. Needs the code
dataset `handball-shot-endtest-code` (same code and models as the end test and the dev run).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
QUEUE = HERE / "observe_queue.json"
OWNER = "lukasde1000"
MAX_SLOTS = 5
# a segment takes 20 min on a fast Kaggle machine and 42 to 50 min on a slow one (the dev run,
# 2026-11-20; the same for 25 to 60 fps): 14 segments fit 12 h on a slow machine only just, so
# the runner also stops starting new segments after GUARD_S and ends cleanly (output kept)
BATCH = 14
GUARD_S = 40_000
# batches 0 to 3 were pushed with 26 segments and no guard before this was known
KEEP_OLD = 4
SLUG = "handball-obs-q{:03d}"
# already observed elsewhere: the dev run (`handball-shot-dev-0..4`)
DEV_LABELS = REPO / "ml/data/segment_labels"
ENDTEST = REPO / "ml/gold/shot_endtest_segments.json"

sys.path.insert(0, str(HERE))


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("KAGGLE_USERNAME", OWNER)
    env.setdefault("KAGGLE_KEY", "placeholder")  # the session's proxy puts in the real key
    if Path("/root/.ccr/ca-bundle.crt").exists():
        env.setdefault("REQUESTS_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")
    return env


def _kaggle(*args: str) -> str:
    r = subprocess.run(
        ["kaggle", *args], capture_output=True, text=True, env=_env(), timeout=180
    )
    return (r.stdout + r.stderr).strip()


def build(library: Path) -> None:
    games: dict[str, tuple[str, dict]] = {}
    for f in sorted((library / "index").glob("*.index.json")):
        ds = f.name.removesuffix(".index.json")
        for g, v in json.loads(f.read_text()).items():
            games[g] = (ds, v)
    endtest = {s["game"] for s in json.loads(ENDTEST.read_text())}
    dev_done: set[str] = set()
    dev_games: list[str] = []
    for f in sorted(DEV_LABELS.glob("*.json")):
        d = json.loads(f.read_text())
        dev_games.append(d["name"])
        for s in d["segments"]:
            if s.get("clock_source") and any(e["segment"] == s["file"] for e in d["entries"]):
                dev_done.add(s["file"])
    order = dev_games + sorted(g for g in games if g not in dev_games)
    segs = []
    for g in order:
        if g in endtest or g not in games:
            continue
        ds, v = games[g]
        for s in v["segments"]:
            if s["file"] not in dev_done:
                segs.append({"game": g, "dataset": ds, "file": s["file"], "fps": v["fps"]})
    old = json.loads(QUEUE.read_text())["batches"][:KEEP_OLD] if QUEUE.exists() else []
    taken = {x["file"] for b in old for x in b}
    rest = [x for x in segs if x["file"] not in taken]
    batches = old + [rest[i : i + BATCH] for i in range(0, len(rest), BATCH)]
    QUEUE.write_text(json.dumps({"batch": BATCH, "batches": batches}, indent=0) + "\n")
    print(len(segs), "segments in", len(batches), "batches ->", QUEUE.relative_to(REPO))


def _status(i: int) -> str:
    out = _kaggle("kernels", "status", f"{OWNER}/{SLUG.format(i)}")
    if "has status" in out:
        return out.rsplit('"', 2)[-2].split(".")[-1].lower()  # running, complete, error, ...
    return "new"


def status() -> list[str]:
    q = json.loads(QUEUE.read_text())
    st = [_status(i) for i in range(len(q["batches"]))]
    for i, s in enumerate(st):
        if s != "new":
            print(SLUG.format(i), s, len(q["batches"][i]), "segments")
    print({s: st.count(s) for s in sorted(set(st))})
    return st


def _runner() -> str:
    from shot_endtest_push import RUNNER  # noqa: PLC0415

    old = "subprocess.run(cmd, env=env, check=True)"
    assert old in RUNNER
    new = (
        "try:\n"
        f"    subprocess.run(cmd, env=env, check=True, timeout={GUARD_S})\n"
        "except subprocess.TimeoutExpired:\n"
        "    print('guard: stopped before the 12 h limit', flush=True)"
    )
    return RUNNER.replace(old, new)


def step() -> None:
    from shot_endtest_push import CODE_SLUG  # noqa: PLC0415

    q = json.loads(QUEUE.read_text())
    st = status()
    # other kernels of the account (e.g. a dev run) take slots as well; Kaggle refuses past the cap
    for i, s in enumerate(st):
        if s != "new":  # an error is reported, not retried: look at its log first
            continue
        part = q["batches"][i]
        with tempfile.TemporaryDirectory() as tmp:
            kd = Path(tmp)
            (kd / "run.py").write_text(_runner().replace("__SEGS__", json.dumps(part)))
            meta = {
                "id": f"{OWNER}/{SLUG.format(i)}",
                "title": SLUG.format(i).replace("-", " "),
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
            out = _kaggle("kernels", "push", "-p", str(kd))
        print(SLUG.format(i), "push:", out.splitlines()[-1] if out else "")
        if "Maximum" in out or "successfully" not in out:
            break  # slots full (or another error): try again at the next step


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("library", type=Path, help="library/ of the dataset handball-library-state")
    sub.add_parser("step")
    sub.add_parser("status")
    a = ap.parse_args()
    if a.cmd == "build":
        build(a.library)
    elif a.cmd == "step":
        step()
    else:
        status()


if __name__ == "__main__":
    main()

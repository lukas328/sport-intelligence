"""Shared test videos (Q-DATA-1): sync real match videos between a bucket and data/videos/.

Videos live in an S3-compatible bucket (Cloudflare R2 in the EU, ADR 002), never in git. The repo
only holds ml/eval/golden_set/manifest.json: one entry per video with object key, checksum and
metadata (camera, venue, consent). No player names in the manifest, it is committed.

Configuration via environment (a read-only token is enough for `list`, `pull` and `check`):

    TESTDATA_S3_ENDPOINT    https://<account-id>.eu.r2.cloudflarestorage.com
    TESTDATA_S3_ACCESS_KEY
    TESTDATA_S3_SECRET_KEY
    TESTDATA_S3_BUCKET      default: handball-testdata
    TESTDATA_S3_REGION      default: auto (R2); e.g. eu-central-1 elsewhere

Commands:

    uv run python scripts/testdata.py check            # credentials and bucket reachable?
    uv run python scripts/testdata.py list             # objects in the bucket vs. manifest
    uv run python scripts/testdata.py pull [ID ...]    # download (all or selected) to data/videos/
    uv run python scripts/testdata.py push FILE --id ID [--camera fixed] [--venue ...] [--minors]
                                                       # upload + add manifest entry (write token)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "ml" / "eval" / "golden_set" / "manifest.json"
VIDEO_DIR = ROOT / "data" / "videos"
PREFIX = "videos/"
CAMERAS = ("fixed", "panning", "auto-follow", "handheld", "unknown")
CONSENT = ("club", "public", "unknown")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,79}$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
CHUNK = 8 * 1024 * 1024


@dataclass(frozen=True)
class Config:
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str
    region: str

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Config:
        env = dict(os.environ) if env is None else env
        missing = [
            name
            for name in ("TESTDATA_S3_ENDPOINT", "TESTDATA_S3_ACCESS_KEY", "TESTDATA_S3_SECRET_KEY")
            if not env.get(name)
        ]
        if missing:
            raise SystemExit(
                "missing environment variables: "
                + ", ".join(missing)
                + "\nsee the docstring of scripts/testdata.py or data/README.md"
            )
        return cls(
            endpoint=env["TESTDATA_S3_ENDPOINT"],
            access_key=env["TESTDATA_S3_ACCESS_KEY"],
            secret_key=env["TESTDATA_S3_SECRET_KEY"],
            bucket=env.get("TESTDATA_S3_BUCKET") or "handball-testdata",
            region=env.get("TESTDATA_S3_REGION") or "auto",
        )


def client(cfg: Config) -> Any:
    import boto3
    from botocore.config import Config as BotoConfig

    return boto3.client(
        "s3",
        endpoint_url=cfg.endpoint,
        region_name=cfg.region,
        aws_access_key_id=cfg.access_key,
        aws_secret_access_key=cfg.secret_key,
        config=BotoConfig(retries={"max_attempts": 5, "mode": "standard"}),
    )


# --- manifest ---------------------------------------------------------------------------------


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("matches", [])
    return data


def save_manifest(data: dict[str, Any], path: Path = MANIFEST) -> None:
    data["matches"] = sorted(data["matches"], key=lambda m: m["id"])
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def local_path(entry: dict[str, Any], video_dir: Path = VIDEO_DIR) -> Path:
    return video_dir / Path(entry["key"]).name


def select(entries: list[dict[str, Any]], ids: Iterable[str]) -> list[dict[str, Any]]:
    wanted = list(ids)
    if not wanted:
        return entries
    by_id = {e["id"]: e for e in entries}
    unknown = [i for i in wanted if i not in by_id]
    if unknown:
        raise SystemExit(f"not in manifest: {', '.join(unknown)}")
    return [by_id[i] for i in wanted]


def probe(path: Path) -> dict[str, Any]:
    """Resolution, fps and duration via ffprobe; empty when ffprobe is missing or fails."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        return {}
    try:
        out = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,avg_frame_rate:format=duration",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            check=True,
            text=True,
            timeout=60,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    info = json.loads(out)
    stream = (info.get("streams") or [{}])[0]
    result: dict[str, Any] = {}
    if stream.get("width") and stream.get("height"):
        result["resolution"] = f"{stream['width']}x{stream['height']}"
    num, _, den = str(stream.get("avg_frame_rate", "")).partition("/")
    if num.isdigit() and den.isdigit() and int(den):
        result["fps"] = round(int(num) / int(den), 2)
    duration = info.get("format", {}).get("duration")
    if duration:
        result["duration_s"] = round(float(duration))
    return result


# --- commands ---------------------------------------------------------------------------------


def cmd_check(s3: Any, cfg: Config) -> int:
    s3.list_objects_v2(Bucket=cfg.bucket, Prefix=PREFIX, MaxKeys=1)
    print(f"ok: bucket {cfg.bucket!r} at {cfg.endpoint} is readable")
    return 0


def list_objects(s3: Any, bucket: str) -> dict[str, int]:
    objects: dict[str, int] = {}
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=PREFIX):
        for obj in page.get("Contents", []):
            objects[obj["Key"]] = int(obj["Size"])
    return objects


def cmd_list(s3: Any, cfg: Config, manifest: dict[str, Any]) -> int:
    objects = list_objects(s3, cfg.bucket)
    known = {e["key"]: e for e in manifest["matches"]}
    for key in sorted(set(objects) | set(known)):
        entry = known.get(key)
        if entry is None:
            state = "bucket only (not in manifest, use push or add an entry)"
        elif key not in objects:
            state = "MISSING in bucket"
        else:
            state = "local" if local_path(entry).exists() else "remote"
        size = objects.get(key, entry.get("bytes", 0) if entry else 0)
        label = entry["id"] if entry else "-"
        print(f"{label:40} {size / 1e6:9.1f} MB  {state:10}  {key}")
    return 0


def cmd_pull(s3: Any, cfg: Config, manifest: dict[str, Any], ids: list[str]) -> int:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    failed = 0
    for entry in select(manifest["matches"], ids):
        target = local_path(entry)
        if target.exists() and sha256(target) == entry["sha256"]:
            print(f"up to date  {entry['id']}")
            continue
        print(f"download    {entry['id']} ({entry.get('bytes', 0) / 1e6:.1f} MB)")
        partial = target.with_suffix(target.suffix + ".part")
        s3.download_file(cfg.bucket, entry["key"], str(partial))
        if sha256(partial) != entry["sha256"]:
            partial.unlink()
            print(f"CHECKSUM MISMATCH {entry['id']}, file removed", file=sys.stderr)
            failed += 1
            continue
        partial.replace(target)
    return 1 if failed else 0


def cmd_push(s3: Any, cfg: Config, manifest: dict[str, Any], args: argparse.Namespace) -> int:
    path = Path(args.file)
    if not path.is_file():
        raise SystemExit(f"no such file: {path}")
    if not ID_RE.match(args.id):
        raise SystemExit("id: lowercase letters, digits and dashes, e.g. 2026-10-12-u17-home")
    digest = sha256(path)
    existing = next((e for e in manifest["matches"] if e["id"] == args.id), None)
    if existing is not None:
        # entry registered before the bucket existed: upload the file, keep the manifest as is
        if existing["sha256"] != digest:
            raise SystemExit(f"id {args.id!r} already in manifest with a different file")
        print(f"upload      {path} -> s3://{cfg.bucket}/{existing['key']} (manifest unchanged)")
        s3.upload_file(str(path), cfg.bucket, existing["key"])
        return 0
    kits = {k: v for k, v in (("home", args.home_kit), ("away", args.away_kit)) if v}
    if any(not HEX_RE.match(v) for v in kits.values()):
        raise SystemExit("kit colours as hex, e.g. --home-kit '#c8102e'")
    key = f"{PREFIX}{args.id}{path.suffix.lower()}"
    print(f"upload      {path} -> s3://{cfg.bucket}/{key}")
    s3.upload_file(str(path), cfg.bucket, key)
    entry: dict[str, Any] = {
        "id": args.id,
        "key": key,
        "sha256": digest,
        "bytes": path.stat().st_size,
        "camera": args.camera,
        "camera_system": args.camera_system,
        "venue": args.venue,
        "level": args.level,
        **probe(path),
        "kits": kits or None,
        "minors": args.minors,
        "consent": args.consent,
        "score": args.score,
        "annotations": None,
        "notes": args.notes,
        "added": datetime.now(UTC).date().isoformat(),
    }
    manifest["matches"].append(entry)
    save_manifest(manifest)
    print(f"added {args.id!r} to {MANIFEST.relative_to(ROOT)}; commit the manifest")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="credentials and bucket reachable")
    sub.add_parser("list", help="bucket objects vs. manifest")
    pull = sub.add_parser("pull", help="download videos to data/videos/")
    pull.add_argument("ids", nargs="*", help="manifest ids (default: all)")
    push = sub.add_parser(
        "push", help="upload a video and add it to the manifest (or upload a registered entry)"
    )
    push.add_argument("file")
    push.add_argument("--id", required=True, help="e.g. 2026-10-12-u17-home (no player names)")
    push.add_argument("--camera", choices=CAMERAS, default="unknown")
    push.add_argument("--camera-system", default=None, help="e.g. Veo, Spiideo, phone")
    push.add_argument("--venue", default=None)
    push.add_argument("--home-kit", default=None, help="shirt colour as hex, e.g. '#c8102e'")
    push.add_argument("--away-kit", default=None, help="shirt colour as hex, e.g. '#f2c200'")
    push.add_argument("--level", default=None, help="league or age group, e.g. U17, 2. Liga")
    push.add_argument("--minors", action="store_true", help="minors are visible in the video")
    push.add_argument("--consent", choices=CONSENT, default="unknown")
    push.add_argument("--score", default=None, help="final score as ground truth, e.g. 28:25")
    push.add_argument("--notes", default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    cfg = Config.from_env()
    s3 = client(cfg)
    manifest = load_manifest()
    if args.cmd == "check":
        return cmd_check(s3, cfg)
    if args.cmd == "list":
        return cmd_list(s3, cfg, manifest)
    if args.cmd == "pull":
        return cmd_pull(s3, cfg, manifest, args.ids)
    return cmd_push(s3, cfg, manifest, args)


if __name__ == "__main__":
    raise SystemExit(main())

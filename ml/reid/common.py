"""Shared pieces of the re-identification scripts: dataset index, cleaning, model."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

MIN_CROPS = 8  # identities with fewer crops are dropped
MIN_ANCHORS = 3  # reading-anchored identities need this many readings (misreads are rare)
MAX_COVERED = 0.5  # crops more than half covered by another person's box are dropped
MAX_KIT_DISTANCE = 40.0  # Lab distance of a crop's shirt colour from its identity's median


def load_index(root: Path) -> list[dict]:
    return json.load(open(root / "index.json"))["crops"]


def shirt_lab(img_bgr: np.ndarray) -> np.ndarray:
    """Median Lab colour of the shirt area (rows 22-45 %, central half) of a 128 x 256 crop."""
    h, w = img_bgr.shape[:2]
    patch = img_bgr[int(0.22 * h) : int(0.45 * h), int(0.3 * w) : int(0.7 * w)]
    lab = cv2.cvtColor(patch, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float64)
    return np.median(lab, axis=0)


def hex_lab(h: str) -> np.ndarray:
    h = h.lstrip("#")
    px = np.array([[[int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16)]]], np.uint8)
    return cv2.cvtColor(px, cv2.COLOR_BGR2LAB).reshape(3).astype(np.float64)


def kit_refs(rows: list[dict], kits: dict[str, str]) -> dict[str, np.ndarray]:
    """Team shirt colours of a clip: start at the manifest kit colours, then the median of the
    crops nearest to each (a few k-means steps; lighting shifts the nominal colours)."""
    refs = {t: hex_lab(kits[t]) for t in ("home", "away")}
    lab = np.array([r["lab"] for r in rows])
    for _ in range(5):
        d = np.stack([np.linalg.norm(lab - refs[t], axis=1) for t in ("home", "away")])
        near = d.argmin(axis=0)
        for k, t in enumerate(("home", "away")):
            m = (near == k) & (d[k] < 60)
            if m.sum() > 20:
                refs[t] = np.median(lab[m], axis=0)
    return refs


def clean(rows: list[dict], root: Path, verbose: bool = True) -> list[dict]:
    """No model involved. Tracks jump between people (also between teams), and the team label of
    a track can be wrong, so:
    - drop crops more than half covered by another person's box;
    - each crop gets its team from its own shirt colour (nearest team colour of the clip, clearly
      nearer than the other, else dropped: referees, goalkeepers, bench, spectators);
    - identity = clip / crop team / voted number (tracklets: the track, majority team only);
    - drop crops whose shirt colour is far from the identity's median, then identities with
      fewer than MIN_CROPS crops."""
    man = json.load(open(Path(__file__).resolve().parents[2] / "ml/eval/golden_set/manifest.json"))
    kits = {m["id"]: m["kits"] for m in man["matches"]}
    rosters: dict[str, dict[str, set[int]]] = {}
    for clip in {r["clip"] for r in rows}:
        rp = Path(__file__).resolve().parents[2] / "ml/eval/official" / f"{clip}.json"
        if rp.exists():
            ro: dict[str, set[int]] = {"home": set(), "away": set()}
            for pl in json.load(open(rp))["players"]:
                if str(pl.get("dressNr", "")).isdigit():
                    ro["home" if pl.get("isHome") else "away"].add(int(pl["dressNr"]))
            rosters[clip] = ro
    rows = [dict(r) for r in rows if r["covered"] <= MAX_COVERED]
    for r in rows:
        if "lab" not in r:
            r["lab"] = shirt_lab(cv2.imread(str(root / r["file"]))).tolist()
    by_clip: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_clip[r["clip"]].append(r)
    kept: list[dict] = []
    off_team = 0
    for clip, rs in by_clip.items():
        refs = kit_refs(rs, kits[clip])
        lab = np.array([r["lab"] for r in rs])
        dh = np.linalg.norm(lab - refs["home"], axis=1)
        da = np.linalg.norm(lab - refs["away"], axis=1)
        for r, h, a in zip(rs, dh, da, strict=True):
            team = "home" if h < a else "away"
            if min(h, a) > MAX_KIT_DISTANCE or abs(h - a) < 15:
                off_team += 1
                continue
            if r.get("numbered", True):
                if clip in rosters and r["number"] not in rosters[clip][team]:
                    off_team += 1  # not on the official roster: misread
                    continue
                r["team"] = team
                r["identity"] = f"{clip}/{team}/{r['number']}"
            else:
                r["kit"] = team
            kept.append(r)
    # tracklets: keep the majority team
    maj: dict[str, str] = {}
    votes: dict[str, list[str]] = defaultdict(list)
    for r in kept:
        if "kit" in r:
            votes[r["identity"]].append(r["kit"])
    for i, v in votes.items():
        maj[i] = max(set(v), key=v.count)
    kept = [r for r in kept if "kit" not in r or r["kit"] == maj[r["identity"]]]
    for r in kept:
        if "kit" in r:
            r["team"] = r.pop("kit")
            r["identity"] = f"{r['clip']}/{r['team']}/{r['identity'].split('/')[-1]}"
    by: dict[str, list[dict]] = defaultdict(list)
    for r in kept:
        by[r["identity"]].append(r)
    out: list[dict] = []
    dropped = 0
    for _i, rs in by.items():
        lab = np.array([r["lab"] for r in rs])
        d = np.linalg.norm(lab - np.median(lab, axis=0), axis=1)
        keep = [r for r, dd in zip(rs, d, strict=True) if dd <= MAX_KIT_DISTANCE * 0.75]
        dropped += len(rs) - len(keep)
        anchors = {r.get("anchor") for r in keep if r.get("anchor") is not None}
        if keep and keep[0].get("anchor") is not None and len(anchors) < MIN_ANCHORS:
            dropped += len(keep)
            continue
        if len(keep) >= MIN_CROPS:
            out += keep
    if verbose:
        num = [r for r in out if r.get("numbered", True)]
        print(
            f"clean: {len(num)} numbered crops of {len({r['identity'] for r in num})} identities"
            f", {len(out) - len(num)} tracklet crops of "
            f"{len({r['identity'] for r in out}) - len({r['identity'] for r in num})} tracklets;"
            f" dropped {off_team} off-team, {dropped} off-identity colour"
        )
    return out


def build_model(dim: int = 256, size: tuple[int, int] = (192, 96), pretrained: bool = True):
    """ResNet18 (ImageNet) + 256-d embedding with BNNeck. Input N x 3 x H x W RGB 0..255 (any
    size; resized inside to `size`), output: training -> (feature, bn feature);
    eval -> L2-normalised bn feature."""
    import torch
    import torch.nn.functional as F  # noqa: N812
    import torchvision
    from torch import nn

    class ReidNet(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            w = torchvision.models.ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
            r = torchvision.models.resnet18(weights=w)
            self.body = nn.Sequential(
                r.conv1, r.bn1, r.relu, r.maxpool, r.layer1, r.layer2, r.layer3, r.layer4
            )
            self.pool = nn.AdaptiveAvgPool2d(1)
            self.fc = nn.Linear(512, dim)
            self.bn = nn.BatchNorm1d(dim)
            self.bn.bias.requires_grad_(False)
            self.size = size
            self.register_buffer("mean", torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1) * 255)
            self.register_buffer("std", torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1) * 255)

        def forward(self, x):  # type: ignore[no-untyped-def]
            if tuple(x.shape[-2:]) != self.size:
                x = F.interpolate(x, size=self.size, mode="bilinear", align_corners=False)
            x = (x - self.mean) / self.std
            f = self.fc(self.pool(self.body(x)).flatten(1))
            b = self.bn(f)
            if self.training:
                return f, b
            return F.normalize(b, dim=1)

    return ReidNet()

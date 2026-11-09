"""Synthetic handball footage with exact ground truth (source: "synthetic").

Renders an elevated sideline camera (perspective, like a club camera on the balcony), fixed or
panning to follow play (`pan` > 0, tripod rotation, optional zoom), with a textured hall: wooden
floor, court lines from the shared court geometry, 2 x 7 players in kit colours with numbers,
2 referees and a ball. Players move in alternating attack and defence phases with switches of side,
crossings and occlusions, so calibration, detection, tracking and team assignment can be measured
without real footage. It is a test instrument, never shown to customers as real analysis.
"""

from __future__ import annotations

import math
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from handball_court import COURT
from handball_vision import geometry

ROLES_ATTACK = {  # attacking positions relative to the attacked goal at x = 40 (metres)
    "LA": (38.5, 1.5),
    "RL": (30.5, 5.5),
    "RM": (29.0, 10.0),
    "RR": (30.5, 14.5),
    "RA": (38.5, 18.5),
    "KM": (34.2, 9.0),
}
ROLES_DEFENCE = {  # 6-0 on the 6 m line of the defended goal at x = 40
    "D1": (39.0, 3.5),
    "D2": (36.0, 6.5),
    "D3": (34.6, 8.8),
    "D4": (34.6, 11.2),
    "D5": (36.0, 13.5),
    "D6": (39.0, 16.5),
}


SPRINT_SPEED = 6.5  # m/s, about 23 km/h
COUNTER_S = 5.0  # a counter after a lost ball is run at sprint speed for this long


@dataclass(frozen=True)
class Kits:
    home: tuple[int, int, int] = (200, 40, 40)  # BGR
    home_gk: tuple[int, int, int] = (40, 200, 230)
    away: tuple[int, int, int] = (230, 230, 235)
    away_gk: tuple[int, int, int] = (60, 170, 60)
    referee: tuple[int, int, int] = (25, 25, 25)


@dataclass(frozen=True)
class SyntheticConfig:
    seconds: float = 30.0
    fps: int = 25
    size: tuple[int, int] = (1280, 720)
    camera: tuple[float, float, float] = (20.0, -12.0, 10.0)
    target: tuple[float, float, float] = (20.0, 8.0, 0.0)
    focal_px: float = 470.0
    phase_s: float = 12.0
    seed: int = 7
    kits: Kits = field(default_factory=Kits)
    noise: float = 3.0  # pixel noise sigma
    pan: float = 0.0  # 0 = fixed camera; 1 = the camera centre follows the centre of play
    zoom: float = 0.0  # relative focal change over a phase (0 = constant focal length)
    walls: bool | None = None  # textured walls (banners, windows); default: on when panning
    # scripted match flow (addendum 01, A3): goals end attacks, throw-offs restart play, sides switch
    restarts: bool = False
    goal_share: float = 0.5
    throw_off_s: float = 8.0  # players walk back and line up (real matches: about 6 to 15 s)
    side_change_s: float | None = None
    # top speed when nothing is at stake: None = everybody always runs at SPRINT_SPEED (a test
    # instrument). With a value (demo footage), players jog between positions and sprint only in
    # the counter after a lost ball, so distances and sprint counts look like a real match
    jog_speed: float | None = None
    tempo: float = 1.0  # pace of the movement around the positions (demo footage: calmer, 0.6)


@dataclass(frozen=True)
class GtObject:
    object_id: int
    label: str  # home, home_gk, away, away_gk, referee, ball
    number: int
    x: float
    y: float
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2 in pixels


@dataclass(frozen=True)
class GtFrame:
    index: int
    t_ms: int
    objects: list[GtObject]
    homography: NDArray[np.float64] | None = None  # court -> image of this frame (panning camera)


@dataclass
class _Agent:
    object_id: int
    label: str
    number: int
    pos: NDArray[np.float64]
    phase: float
    speed: float


# Demo footage (scripts/seed.py): goals and throw-offs, attacks of 25 s, a calm set play, jogging
# between positions and sprints only in counters. Field players then cover about 100 m per minute
# with a few sprints, like a real match; the test default (every 12 s a turnover with the whole team
# sprinting across the court) gives about 190 m per minute and a fast break in every attack.
DEMO: dict[str, Any] = {"restarts": True, "phase_s": 25.0, "jog_speed": 4.0, "tempo": 0.4}


class SyntheticMatch:
    def __init__(self, cfg: SyntheticConfig | None = None) -> None:
        self.cfg = cfg or SyntheticConfig()
        self._view_x = self.cfg.target[0]
        self._set_camera(0.0)
        rng = np.random.default_rng(self.cfg.seed)
        self.rng = rng
        self._banners = self._make_banners(np.random.default_rng(self.cfg.seed + 1000))
        self.agents: list[_Agent] = []
        oid = 1
        for team in ("home", "away"):
            numbers = rng.choice(np.arange(2, 40), size=6, replace=False)
            for n in numbers:
                self.agents.append(
                    _Agent(
                        oid,
                        team,
                        int(n),
                        rng.uniform([10, 3], [30, 17]),
                        rng.uniform(0, 2 * math.pi),
                        rng.uniform(0.6, 1.2),
                    )
                )
                oid += 1
            self.agents.append(
                _Agent(
                    oid, f"{team}_gk", 1 if team == "home" else 12, np.array([1.5, 10.0]), 0.0, 0.5
                )
            )
            oid += 1
        for _ in range(2):
            self.agents.append(
                _Agent(oid, "referee", 0, rng.uniform([12, 1], [28, 19]), rng.uniform(0, 6), 0.5)
            )
            oid += 1
        flow = np.random.default_rng(self.cfg.seed + 101)  # separate stream: positions unchanged
        phases = int(self.cfg.seconds // self.cfg.phase_s) + 2
        self.outcomes = [
            "goal" if flow.random() < self.cfg.goal_share else "lost" for _ in range(phases)
        ]
        self._background = self._render_background()
        w, h = self.cfg.size
        # a few precomputed noise fields, cycled per frame (sensor noise without per-frame cost)
        self._noise = (
            [rng.normal(0, self.cfg.noise, (h, w, 3)).astype(np.int16) for _ in range(6)]
            if self.cfg.noise
            else []
        )

    @property
    def moving(self) -> bool:
        return self.cfg.pan > 0 or self.cfg.zoom > 0

    def _set_camera(self, t: float) -> None:
        cfg = self.cfg
        _, ty, tz = cfg.target
        focal = cfg.focal_px * (1 + cfg.zoom * 0.5 * (1 - math.cos(2 * math.pi * t / cfg.phase_s)))
        self.p = geometry.look_at_camera(cfg.camera, (self._view_x, ty, tz), focal, cfg.size)
        self.h = geometry.ground_homography(self.p)  # court -> image

    def _follow(self, dt: float) -> None:
        """Camera operator: aim at the centre of the field players, with some lag."""
        xs = [a.pos[0] for a in self.agents if a.label in ("home", "away")]
        goal = self.cfg.target[0] + self.cfg.pan * (float(np.mean(xs)) - self.cfg.target[0])
        self._view_x += (goal - self._view_x) * min(1.0, dt * 1.5)

    def _clip_project(
        self, poly: NDArray[np.float64], near: float = 0.3
    ) -> NDArray[np.int32] | None:
        """Project a planar 3D polygon, clipped against the camera's near plane."""
        hom = np.hstack([poly, np.ones((len(poly), 1))]) @ self.p.T
        depth = hom[:, 2]
        out = []
        for k in range(len(poly)):
            a, b = hom[k], hom[(k + 1) % len(poly)]
            da, db = depth[k], depth[(k + 1) % len(poly)]
            if da > near:
                out.append(a)
            if (da > near) != (db > near):
                s = (near - da) / (db - da)
                out.append(a + s * (b - a))
        if len(out) < 3:
            return None
        arr = np.array(out)
        pts = np.clip(arr[:, :2] / arr[:, 2:3], -1e5, 1e5)
        return pts.round().astype(np.int32)

    def _make_banners(
        self, rng: np.random.Generator
    ) -> list[tuple[NDArray[np.float64], tuple[int, int, int]]]:
        """Wall texture as 3D quads: ad banners, windows and pillars (needed to track a moving camera)."""
        quads: list[tuple[NDArray[np.float64], tuple[int, int, int]]] = []

        def colour() -> tuple[int, int, int]:
            c = rng.integers(30, 250, 3)
            return (int(c[0]), int(c[1]), int(c[2]))

        x = -6.0
        while x < 46:  # far wall (y = 24)
            w = float(rng.uniform(2.0, 4.5))
            quads.append(
                (
                    np.array([[x, 24, 0.2], [x + w, 24, 0.2], [x + w, 24, 1.2], [x, 24, 1.2]]),
                    colour(),
                )
            )
            if rng.random() < 0.5:
                quads.append(
                    (
                        np.array(
                            [
                                [x + 0.3, 24, 4],
                                [x + w - 0.3, 24, 4],
                                [x + w - 0.3, 24, 6.5],
                                [x + 0.3, 24, 6.5],
                            ]
                        ),
                        (225, 220, 205),
                    )
                )
            quads.append(
                (
                    np.array(
                        [[x + w, 24, 0], [x + w + 0.4, 24, 0], [x + w + 0.4, 24, 8], [x + w, 24, 8]]
                    ),
                    (90, 95, 110),
                )
            )
            x += w + 0.6
        for wx in (-6.0, 46.0):  # end walls
            y = -8.0
            while y < 24:
                d = float(rng.uniform(2.0, 4.0))
                quads.append(
                    (
                        np.array([[wx, y, 0.2], [wx, y + d, 0.2], [wx, y + d, 1.4], [wx, y, 1.4]]),
                        colour(),
                    )
                )
                y += d + 0.8
        return quads

    # ---- motion --------------------------------------------------------------------------

    def _side_change_phase(self) -> int | None:
        sc = self.cfg.side_change_s
        return None if sc is None else round(sc / self.cfg.phase_s)

    def restart(self, phase: int) -> bool:
        """True when the phase starts with a throw-off (match start, after a goal, new half)."""
        if not self.cfg.restarts:
            return False
        return (
            phase == 0 or self.outcomes[phase - 1] == "goal" or phase == self._side_change_phase()
        )

    def attack_right(self, phase: int) -> bool:
        """Home attacks the right goal until the side change, then the left one."""
        home_attacks = phase % 2 == 0
        sc = self._side_change_phase()
        flipped = sc is not None and phase >= sc
        return home_attacks != flipped

    def events(self) -> list[dict[str, object]]:
        """Ground-truth match events of the scripted flow (t_ms, type, team)."""
        cfg = self.cfg
        out: list[dict[str, object]] = []
        n = int(cfg.seconds // cfg.phase_s) + 1
        for p in range(n):
            start = p * cfg.phase_s
            attack = "home" if p % 2 == 0 else "away"
            if p and start < cfg.seconds:
                prev = "away" if attack == "home" else "home"
                if cfg.restarts and self.outcomes[p - 1] == "goal":
                    out.append({"t_ms": round((start - 1.0) * 1000), "type": "goal", "team": prev})
                out.append(
                    {"t_ms": round(start * 1000), "type": "possession_change", "team": attack}
                )
                if p == self._side_change_phase():
                    out.append({"t_ms": round(start * 1000), "type": "side_change", "team": None})
            if self.restart(p) and start + cfg.throw_off_s < cfg.seconds:
                t_ms = round((start + cfg.throw_off_s) * 1000)
                out.append({"t_ms": t_ms, "type": "throw_off", "team": attack})
        return sorted(out, key=lambda e: int(str(e["t_ms"])))

    def _targets(self, t: float) -> dict[int, NDArray[np.float64]]:
        phase = int(t // self.cfg.phase_s)
        home_attacks = phase % 2 == 0
        attack_right = self.attack_right(phase)
        attack, defend = ("home", "away") if home_attacks else ("away", "home")
        out: dict[int, NDArray[np.float64]] = {}
        local = t - phase * self.cfg.phase_s
        if self.restart(phase) and local < self.cfg.throw_off_s:
            # throw-off: both teams in their own half, the throwing team at the centre
            for team in (attack, defend):
                players = [a for a in self.agents if a.label == team]
                own_left = (team == attack) == attack_right
                for k, a in enumerate(players):
                    # positions in left-half coordinates, mirrored for the right half
                    if team == attack and k == 0:
                        x, y = 19.6, 10.0
                    else:
                        x, y = 16.0 - (k % 2) * 3, 3.0 + k * 2.8
                    if not own_left:
                        x = 40 - x
                    out[a.object_id] = np.array([x, y])
        tm = t * self.cfg.tempo  # the movement around the positions runs on this clock
        sway = math.sin(tm * 0.9) * 2.0  # ball side moves left and right
        for team, roles in ((attack, ROLES_ATTACK), (defend, ROLES_DEFENCE)):
            players = [a for a in self.agents if a.label == team]
            if players and players[0].object_id in out:
                continue
            for a, (_, (x, y)) in zip(players, roles.items(), strict=True):
                dx = 1.4 * math.sin(tm * 1.3 * a.speed + a.phase)
                dy = 1.2 * math.cos(tm * 1.1 * a.speed + a.phase) + (
                    sway * 0.6 if team == defend else sway * 0.3
                )
                px, py = x + dx, float(np.clip(y + dy, 0.6, 19.4))
                if not attack_right:  # mirror to the left goal
                    px, py = 40 - px, 20 - py
                out[a.object_id] = np.array([px, py])
        for a in self.agents:
            if a.label.endswith("_gk"):
                team = a.label[:-3]
                defending_right = (team == defend) == attack_right
                gx = 38.6 if defending_right else 1.4
                if team == attack:  # the attacking team's goalkeeper waits deep in his own half
                    gx = 1.6 if attack_right else 38.4
                out[a.object_id] = np.array([gx, 10 + 1.5 * math.sin(t * 0.7 + a.object_id)])
            elif a.label == "referee":
                side = 1 if a.object_id % 2 else -1
                out[a.object_id] = np.array(
                    [20 + side * 9 + 3 * math.sin(t * 0.4), 0.8 if side > 0 else 19.2]
                )
        return out

    def _speed(self, t: float) -> float:
        """Top speed (m/s) at time t: a sprint in the first seconds after a lost ball, else a jog."""
        cfg = self.cfg
        if cfg.jog_speed is None:
            return SPRINT_SPEED
        phase = int(t // cfg.phase_s)
        counter = phase > 0 and self.outcomes[phase - 1] == "lost" and not self.restart(phase)
        return SPRINT_SPEED if counter and t - phase * cfg.phase_s < COUNTER_S else cfg.jog_speed

    def _step(self, t: float, dt: float) -> None:
        targets = self._targets(t)
        speed = self._speed(t)
        for a in self.agents:
            d = targets[a.object_id] - a.pos
            dist = float(np.linalg.norm(d))
            vmax = speed * dt  # m per frame
            a.pos = a.pos + (d if dist <= vmax else d / dist * vmax)

    # ---- rendering -----------------------------------------------------------------------

    def _render_background(self) -> NDArray[np.uint8]:
        w, h = self.cfg.size
        img = np.zeros((h, w, 3), np.uint8)
        img[:] = (40, 45, 55)  # hall walls
        walls = self.cfg.walls if self.cfg.walls is not None else self.moving
        if walls:
            for quad, col in self._banners:
                poly = self._clip_project(quad)
                if poly is not None:
                    cv2.fillPoly(img, [poly], col)
        floor = self._clip_project(
            np.array([[-6, -8, 0], [46, -8, 0], [46, 24, 0], [-6, 24, 0]], float)
        )
        if floor is not None:
            cv2.fillPoly(img, [floor], (70, 135, 185))  # wooden floor (BGR)
        # stripes of the parquet
        for x in np.arange(-4, 44, 0.5):
            seg = geometry.apply(self.h, np.array([[x, -3], [x, 23]])).astype(np.int32)
            shade = 6 if int(x * 2) % 2 else -6
            cv2.line(
                img,
                tuple(seg[0]),
                tuple(seg[1]),
                (70 + shade, 135 + shade, 185 + shade),
                1,
                cv2.LINE_AA,
            )
        for name in ("goal_area_left", "goal_area_right"):
            area = geometry.apply(self.h, np.array(COURT.lines[name]))
            cv2.fillPoly(img, [area.astype(np.int32)], (150, 110, 60))
        for name, pts in COURT.lines.items():
            if name.startswith("substitution"):
                continue
            img_pts = geometry.apply(self.h, np.array(pts)).astype(np.int32)
            thick = 4 if name.startswith("goal_left") or name.startswith("goal_right") else 2
            color = (
                (40, 40, 220)
                if name.startswith("goal_") and not name.startswith("goal_area")
                else (245, 245, 245)
            )
            if name in COURT.dashed_lines:
                for i in range(0, len(img_pts) - 1, 2):
                    cv2.line(
                        img, tuple(img_pts[i]), tuple(img_pts[i + 1]), color, thick, cv2.LINE_AA
                    )
            else:
                cv2.polylines(img, [img_pts], False, color, thick, cv2.LINE_AA)
        return img

    def _bbox(self, x: float, y: float, height_m: float) -> tuple[float, float, float, float]:
        foot, head = geometry.project(self.p, np.array([[x, y, 0.0], [x, y, height_m]]))
        hpx = foot[1] - head[1]
        wpx = hpx * 0.32
        return (foot[0] - wpx / 2, head[1], foot[0] + wpx / 2, foot[1])

    def frames(self) -> Iterator[tuple[NDArray[np.uint8], GtFrame]]:
        cfg = self.cfg
        n = round(cfg.seconds * cfg.fps)
        dt = 1 / cfg.fps
        kits = cfg.kits
        colors = {
            "home": kits.home,
            "home_gk": kits.home_gk,
            "away": kits.away,
            "away_gk": kits.away_gk,
            "referee": kits.referee,
        }
        for i in range(n):
            t = i * dt
            self._step(t, dt)
            if self.moving:
                self._follow(dt)
                self._set_camera(t)
                self._background = self._render_background()
            img = self._background.copy()
            objects: list[GtObject] = []
            # painter's algorithm: far players first
            for a in sorted(self.agents, key=lambda a: -a.pos[1]):
                x, y = float(a.pos[0]), float(a.pos[1])
                x1, y1, x2, y2 = self._bbox(x, y, 1.85 if a.label != "referee" else 1.8)
                objects.append(GtObject(a.object_id, a.label, a.number, x, y, (x1, y1, x2, y2)))
                body_top = y1 + (y2 - y1) * 0.16
                skin, shorts = (
                    (150, 180, 220),
                    (30, 30, 30) if a.label != "away" else (220, 220, 220),
                )
                cx, w = (x1 + x2) / 2, x2 - x1
                head_r = max(2, int(w * 0.32))
                cv2.circle(img, (int(cx), int(y1 + head_r)), head_r, skin, -1, cv2.LINE_AA)
                cv2.rectangle(
                    img,
                    (int(x1), int(body_top)),
                    (int(x2), int(y1 + (y2 - y1) * 0.55)),
                    colors[a.label],
                    -1,
                )
                cv2.rectangle(
                    img,
                    (int(x1 + w * 0.08), int(y1 + (y2 - y1) * 0.55)),
                    (int(x2 - w * 0.08), int(y1 + (y2 - y1) * 0.7)),
                    shorts,
                    -1,
                )
                stride = math.sin(t * 9 + a.object_id) * w * 0.18
                for leg in (-1, 1):
                    lx = cx + leg * w * 0.18 + leg * stride
                    cv2.line(
                        img,
                        (int(cx + leg * w * 0.15), int(y1 + (y2 - y1) * 0.7)),
                        (int(lx), int(y2)),
                        skin,
                        max(1, int(w * 0.18)),
                        cv2.LINE_AA,
                    )
                if a.number and w > 10:
                    text_color = (255, 255, 255) if sum(colors[a.label]) < 400 else (20, 20, 20)
                    cv2.putText(
                        img,
                        str(a.number),
                        (int(cx - w * 0.3), int(y1 + (y2 - y1) * 0.45)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        max(0.25, w / 40),
                        text_color,
                        1,
                        cv2.LINE_AA,
                    )
            # ball near the court centre of the attack
            bx, by = 31.0 + 3 * math.sin(t * 1.7), 10 + 6 * math.sin(t * 0.9)
            if not self.attack_right(int(t // cfg.phase_s)):
                bx = 40 - bx
            ball = geometry.project(self.p, np.array([[bx, by, 1.2 + 0.4 * math.sin(t * 5)]]))[0]
            cv2.circle(img, (int(ball[0]), int(ball[1])), 3, (40, 200, 240), -1, cv2.LINE_AA)
            if self._noise:
                img = np.clip(
                    img.astype(np.int16) + self._noise[i % len(self._noise)], 0, 255
                ).astype(np.uint8)
            yield img, GtFrame(i, round(t * 1000), objects, self.h.copy() if self.moving else None)

    def write(self, path: Path, ffmpeg: str = "ffmpeg") -> list[GtFrame]:
        w, h = self.cfg.size
        proc = subprocess.Popen(  # noqa: S603
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "bgr24",
                "-s",
                f"{w}x{h}",
                "-r",
                str(self.cfg.fps),
                "-i",
                "pipe:0",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                str(path),
            ],
            stdin=subprocess.PIPE,
        )
        assert proc.stdin is not None
        truth = []
        for img, gt in self.frames():
            proc.stdin.write(img.tobytes())
            truth.append(gt)
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg failed to encode synthetic video")
        return truth


def main() -> None:
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Render a synthetic handball clip with ground truth")
    ap.add_argument("out", type=Path)
    ap.add_argument("--seconds", type=float, default=30)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--truth", type=Path, help="write ground truth JSON here")
    ap.add_argument("--demo", action="store_true", help="match-like flow for demo data (DEMO)")
    args = ap.parse_args()
    extra = DEMO if args.demo else {}
    match = SyntheticMatch(SyntheticConfig(seconds=args.seconds, seed=args.seed, **extra))
    truth = match.write(args.out)
    if args.truth:
        args.truth.write_text(
            json.dumps(
                {
                    "source": "synthetic",
                    "homography": match.h.tolist(),
                    "fps": match.cfg.fps,
                    "frames": [
                        {
                            "t_ms": f.t_ms,
                            "objects": [
                                {
                                    "id": o.object_id,
                                    "label": o.label,
                                    "number": o.number,
                                    "x": round(o.x, 3),
                                    "y": round(o.y, 3),
                                }
                                for o in f.objects
                            ],
                        }
                        for f in truth
                    ],
                }
            )
        )


if __name__ == "__main__":
    main()

"""Camera motion (BRIEF 7.2 stage 2a): map every frame of a fixed, panning or zooming camera onto
one virtual fixed camera (the "canvas").

Club and broadcast cameras stand on a tripod and only rotate (pan, tilt) and zoom. Under that model
two frames are related by H = K_a R_ab K_b^-1, so all frames can be placed on one panorama of the
hall. Every later stage (calibration, background model, detection, tracking) then works on the
canvas as on a fixed camera; a fixed camera is the special case canvas = frame.

1. Frame to frame: KLT tracks on a downscaled grey image, RANSAC homography, projected onto the
   rotation + zoom model (4 degrees of freedom instead of 8, so errors do not grow into distortions).
2. Drift: every `keyframe_every` frames the frame is registered (ORB + RANSAC) against earlier
   keyframes that look at the same part of the hall, which pulls the chain back (loop closure).
3. A cut or lost track starts a new segment; it is placed once one of its keyframes registers
   against a placed keyframe. Segments that never connect (close-ups, replays, other cameras) are
   dropped, their frames have no homography.
4. The focal length is estimated from all keyframe registrations (rotation-only consistency).
5. The reference view is the median viewing direction; the canvas is the bounding box of all
   placed frames (capped in size).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

F64 = NDArray[np.float64]
U8 = NDArray[Any]

MAX_VIEW_ANGLE = np.radians(70)  # frames looking further away from the reference are dropped


@dataclass
class CameraMotion:
    """Per-frame camera orientation and zoom, plus a planar canvas (virtual wide camera).

    Rotations map world directions into camera coordinates (camera at the origin, x right, y down,
    z forward); focal lengths are in full-resolution pixels with the principal point at the image
    centre. The canvas is a pinhole view with rotation `ref_r`, focal `canvas_f` and principal point
    `canvas_c`, limited to `MAX_VIEW_ANGLE` around its axis so it never degenerates.
    """

    frame_size: tuple[int, int]
    moving: bool
    rotations: list[F64 | None]
    focals: list[float]
    ref_r: F64 = field(default_factory=lambda: np.eye(3))
    canvas_f: float = 1.0
    canvas_c: tuple[float, float] = (0.0, 0.0)
    canvas_size: tuple[int, int] = (0, 0)
    samples: list[tuple[int, U8]] = field(default_factory=list, repr=False)
    stats: dict[str, float] = field(default_factory=dict)
    panorama: U8 | None = field(default=None, repr=False)  # cached background of the canvas

    def save(self, path: Path) -> None:
        """Rotations, focal lengths, canvas and panorama (re-runs skip the motion pass)."""
        n = len(self.rotations)
        rots = np.full((n, 3, 3), np.nan)
        for i, r in enumerate(self.rotations):
            if r is not None:
                rots[i] = r
        meta = {
            "frame_size": list(self.frame_size),
            "moving": self.moving,
            "canvas_f": self.canvas_f,
            "canvas_c": list(self.canvas_c),
            "canvas_size": list(self.canvas_size),
            "stats": self.stats,
        }
        arrays: dict[str, Any] = {
            "rotations": rots,
            "focals": np.array(self.focals, np.float64),
            "ref_r": self.ref_r,
            "meta": np.array(json.dumps(meta)),
        }
        if self.panorama is not None:
            arrays["panorama"] = self.panorama
            arrays["seen"] = self.seen()
        with path.open("wb") as fh:
            np.savez_compressed(fh, **arrays)

    @classmethod
    def load(cls, path: Path) -> CameraMotion:
        with np.load(path, allow_pickle=False) as data:
            meta = json.loads(str(data["meta"]))
            motion = cls(
                (int(meta["frame_size"][0]), int(meta["frame_size"][1])),
                bool(meta["moving"]),
                [
                    None if np.isnan(r).any() else np.asarray(r, np.float64)
                    for r in data["rotations"]
                ],
                [float(x) for x in data["focals"]],
                ref_r=np.asarray(data["ref_r"], np.float64),
                canvas_f=float(meta["canvas_f"]),
                canvas_c=(float(meta["canvas_c"][0]), float(meta["canvas_c"][1])),
                canvas_size=(int(meta["canvas_size"][0]), int(meta["canvas_size"][1])),
                stats={k: float(v) for k, v in meta["stats"].items()},
                panorama=np.asarray(data["panorama"]) if "panorama" in data else None,
            )
            if "seen" in data:
                motion.__dict__["_seen"] = np.asarray(data["seen"])
        return motion

    @classmethod
    def fixed(cls, size: tuple[int, int], frames: int) -> CameraMotion:
        w, h = size
        return cls(
            size,
            False,
            [np.eye(3)] * frames,
            [float(w)] * frames,
            canvas_f=float(w),
            canvas_c=(w / 2, h / 2),
            canvas_size=size,
        )

    def __len__(self) -> int:
        return len(self.rotations)

    def registered(self, index: int) -> bool:
        return self._r(index) is not None

    def _r(self, index: int) -> F64 | None:
        return self.rotations[min(index, len(self.rotations) - 1)] if self.rotations else None

    @property
    def coverage(self) -> float:
        n = len(self.rotations)
        return sum(r is not None for r in self.rotations) / n if n else 0.0

    def _k_frame(self, index: int) -> F64:
        w, h = self.frame_size
        f = self.focals[min(index, len(self.focals) - 1)]
        return np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1.0]])

    def canvas_intrinsics(self) -> F64:
        """Pinhole matrix of the canvas (known focal length: lets calibration check the court)."""
        return self._k_canvas()

    def _k_canvas(self) -> F64:
        return np.array(
            [
                [self.canvas_f, 0, self.canvas_c[0]],
                [0, self.canvas_f, self.canvas_c[1]],
                [0, 0, 1.0],
            ]
        )

    def frame_to_canvas(self, index: int) -> F64 | None:
        """Homography frame px -> canvas px (valid for directions in front of the canvas)."""
        if not self.moving:
            return np.eye(3) if self.registered(index) else None
        r = self._r(index)
        if r is None:
            return None
        return self._k_canvas() @ self.ref_r @ r.T @ np.linalg.inv(self._k_frame(index))

    def canvas_to_frame(self, index: int) -> F64 | None:
        h = self.frame_to_canvas(index)
        return None if h is None else np.asarray(np.linalg.inv(h), np.float64)

    def _remap(
        self, rays: F64, r: F64, k: F64, shape: tuple[int, int], limit: float
    ) -> tuple[U8, U8]:
        """Maps for cv2.remap: target pixels (given as world rays) -> source pixels via (r, k)."""
        cam = rays @ r.T.astype(np.float32)
        z = cam[:, 2]
        ok = z > np.float32(np.cos(limit)) * np.linalg.norm(cam, axis=1)
        zs = np.where(ok, z, 1.0)
        x = k[0, 0] * cam[:, 0] / zs + k[0, 2]
        y = k[1, 1] * cam[:, 1] / zs + k[1, 2]
        x = np.where(ok, x, -1.0).astype(np.float32).reshape(shape)
        y = np.where(ok, y, -1.0).astype(np.float32).reshape(shape)
        return x, y

    def _grid(self, k: F64, r: F64, size: tuple[int, int]) -> F64:
        cache: dict[tuple[int, int], F64] = self.__dict__.setdefault("_pix", {})
        pix = cache.get(size)
        if pix is None:
            w, h = size
            xs, ys = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
            pix = np.stack([xs.ravel(), ys.ravel(), np.ones(w * h, np.float32)], axis=1)
            cache[size] = pix
        m = (np.linalg.inv(k).T @ r).astype(np.float32)
        return np.asarray(pix @ m)  # world rays (float32)

    def warp_to_canvas(self, frame: U8, index: int) -> tuple[U8, U8] | None:
        """Frame on the canvas plus the mask of canvas pixels it covers (None if unregistered)."""
        r = self._r(index)
        if r is None:
            return None
        if not self.moving:
            return frame, np.full(frame.shape[:2], 255, np.uint8)
        w, h = self.canvas_size
        rays = self.__dict__.get("_canvas_rays")
        if rays is None:
            rays = self.__dict__["_canvas_rays"] = self._grid(
                self._k_canvas(), self.ref_r, self.canvas_size
            )
        mx, my = self._remap(rays, r, self._k_frame(index), (h, w), np.radians(89))
        img = cv2.remap(frame, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        fw, fh = self.frame_size
        valid = ((mx >= 2) & (my >= 2) & (mx < fw - 3) & (my < fh - 3)).astype(np.uint8) * 255
        return img, valid

    def render_from_canvas(
        self, canvas: U8, index: int, scale: float = 1.0
    ) -> tuple[U8, U8] | None:
        """Canvas image (e.g. the background) seen by frame `index`, at `scale` of the frame size."""
        r = self._r(index)
        if r is None:
            return None
        fw, fh = self.frame_size
        size = (round(fw * scale), round(fh * scale))
        if not self.moving:
            img = canvas if scale == 1 else cv2.resize(canvas, size, interpolation=cv2.INTER_AREA)
            return img, np.full((size[1], size[0]), 255, np.uint8)
        ks = np.diag([scale, scale, 1.0]) @ self._k_frame(index)
        rays = self._grid(ks, r, size)
        mx, my = self._remap(rays, self.ref_r, self._k_canvas(), (size[1], size[0]), MAX_VIEW_ANGLE)
        img = cv2.remap(canvas, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        cw, ch = self.canvas_size
        valid = ((mx >= 0) & (my >= 0) & (mx < cw - 1) & (my < ch - 1)).astype(np.uint8) * 255
        return img, valid

    def background(self, band: int = 96) -> U8:
        """Median canvas image over the kept samples (players and overlays move, the hall does not).

        Samples are warped once (uint8 + coverage mask), the median is taken band by band so memory
        stays at a few hundred MB even for wide canvases.
        """
        if self.panorama is not None:
            return self.panorama
        if not self.samples:
            raise ValueError("no samples kept")
        if not self.moving:
            self.panorama = np.median(np.stack([f for _, f in self.samples]), axis=0).astype(
                np.uint8
            )
            return self.panorama
        w, h = self.canvas_size
        imgs = np.zeros((len(self.samples), h, w, 3), np.uint8)
        masks = np.zeros((len(self.samples), h, w), bool)
        for k, (i, frame) in enumerate(self.samples):
            warped = self.warp_to_canvas(frame, i)
            if warped is not None:
                imgs[k], masks[k] = warped[0], warped[1] > 0
        self.__dict__["_seen"] = masks.any(axis=0).astype(np.uint8) * 255
        out = np.zeros((h, w, 3), np.uint8)
        for y in range(0, h, band):
            blk = imgs[:, y : y + band].astype(np.float32)
            blk[~masks[:, y : y + band]] = np.inf  # sorted to the end
            blk.sort(axis=0)
            count = masks[:, y : y + band].sum(axis=0)  # samples per pixel
            mid = np.maximum(count - 1, 0) // 2
            med = np.take_along_axis(blk, mid[None, :, :, None].repeat(3, axis=3), axis=0)[0]
            med[count == 0] = 0
            out[y : y + band] = med.astype(np.uint8)
        self.panorama = out
        return out

    def seen(self) -> U8:
        """Canvas pixels covered by at least one kept sample (cached by `background`)."""
        cached = self.__dict__.get("_seen")
        if cached is not None:
            return np.asarray(cached)
        w, h = self.canvas_size
        if not self.moving:
            return np.full((h, w), 255, np.uint8)
        mask = np.zeros((h, w), np.uint8)
        for i, frame in self.samples:
            warped = self.warp_to_canvas(frame, i)
            if warped is not None:
                mask |= warped[1]
        return mask


# --- rotation + zoom geometry (pixel coordinates centred on the principal point) ---------------


Corr = tuple[NDArray[np.float64], NDArray[np.float64]]  # (src, dst) centred work px


def _rodrigues(w: F64) -> F64:
    theta = float(np.linalg.norm(w))
    k = np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])
    if theta < 1e-9:
        return np.asarray(np.eye(3) + k, np.float64)
    k = k / theta
    return np.asarray(np.eye(3) + np.sin(theta) * k + (1 - np.cos(theta)) * k @ k, np.float64)


def _log_rot(r: F64) -> F64:
    vec, _ = cv2.Rodrigues(r)
    return np.asarray(vec.ravel(), np.float64)


def _project(params: F64, src: F64, f_dst: float) -> F64:
    r = _rodrigues(params[:3])
    f_src = f_dst * float(np.exp(params[3]))
    rays = np.column_stack([src / f_src, np.ones(len(src))]) @ r.T
    z = np.where(np.abs(rays[:, 2]) < 1e-6, 1e-6, rays[:, 2])
    return np.asarray(f_dst * rays[:, :2] / z[:, None], np.float64)


def fit_rotation(
    src: F64, dst: F64, f_dst: float, r0: F64 | None = None, zoom: bool = True, delta: float = 1.5
) -> tuple[F64, float, float]:
    """Rotation R (src camera -> dst camera) and zoom f_src / f_dst from point pairs.

    Gauss-Newton with Huber weights on the reprojection error (centred px). Returns (R, zoom, rms of
    the inliers in px).
    """
    p = np.zeros(4)
    if r0 is not None:
        p[:3] = _log_rot(r0)
    n_par = 4 if zoom else 3
    eps = 1e-6
    for _ in range(8):
        res = (_project(p, src, f_dst) - dst).ravel()
        jac = np.empty((len(res), n_par))
        for k in range(n_par):
            dp = p.copy()
            dp[k] += eps
            jac[:, k] = ((_project(dp, src, f_dst) - dst).ravel() - res) / eps
        a = np.abs(res)
        wgt = np.where(a <= delta, 1.0, delta / np.maximum(a, 1e-12))
        jw = jac * wgt[:, None]
        try:
            step = np.linalg.solve(jw.T @ jac + 1e-9 * np.eye(n_par), -(jw.T @ res))
        except np.linalg.LinAlgError:
            break
        p[:n_par] += step
        if float(np.abs(step).max()) < 1e-7:
            break
    err = np.linalg.norm(_project(p, src, f_dst) - dst, axis=1)
    inl = err < 3 * delta
    rms = float(np.sqrt(np.mean(err[inl] ** 2))) if inl.sum() >= 8 else float("inf")
    return _rodrigues(p[:3]), float(np.exp(p[3])), rms


def estimate_focal(corrs: list[Corr], width: float, zooms: list[float] | None = None) -> float:
    """Focal length (px) that makes the registrations most consistent with pure rotations.

    `zooms` gives the relative focal of each pair's destination frame (1.0 = reference frame).
    """
    if len(corrs) < 3:
        return width
    zl = zooms or [1.0] * len(corrs)

    def score(f: float) -> float:
        return float(
            np.mean(
                [
                    min(fit_rotation(s, d, f * z)[2], 5.0)
                    for (s, d), z in zip(corrs, zl, strict=True)
                ]
            )
        )

    fs = np.geomspace(0.4 * width, 4.0 * width, 25)
    i = int(np.argmin([score(f) for f in fs]))
    lo, hi = np.log(fs[max(0, i - 1)]), np.log(fs[min(len(fs) - 1, i + 1)])
    g = (np.sqrt(5) - 1) / 2  # golden-section search in log f
    a, b = hi - g * (hi - lo), lo + g * (hi - lo)
    sa, sb = score(float(np.exp(a))), score(float(np.exp(b)))
    for _ in range(12):
        if sa < sb:
            hi, b, sb = b, a, sa
            a = hi - g * (hi - lo)
            sa = score(float(np.exp(a)))
        else:
            lo, a, sa = a, b, sb
            b = lo + g * (hi - lo)
            sb = score(float(np.exp(b)))
    return float(np.exp((lo + hi) / 2))


def _axis(r: F64) -> F64:
    return np.asarray(r[2], np.float64)  # optical axis in world coordinates


def _angle(r1: F64, r2: F64) -> float:
    return float(np.arccos(np.clip((np.trace(r1 @ r2.T) - 1) / 2, -1, 1)))


@dataclass
class _Keyframe:
    index: int
    kp: NDArray[np.float32]
    desc: U8


class _Poses:
    """Sequential solver: per-frame rotation (world -> camera) and focal from steps and anchors."""

    def __init__(self, f0: float) -> None:
        self.f0 = f0
        self.r: list[F64 | None] = []
        self.f: list[float] = []
        self.seg: list[int] = []
        self.placed: set[int] = {0}
        self.corrections: list[float] = []

    def step(self, corr: Corr | None) -> None:
        i = len(self.r)
        if i == 0 or corr is None or self.r[-1] is None:
            seg = (self.seg[-1] + 1) if i else 0
            self.r.append(np.eye(3))
            self.f.append(self.f0 if i == 0 else self.f[-1])
            self.seg.append(seg)
            return
        prev_r = self.r[-1]
        assert prev_r is not None
        r_pc, z, _ = fit_rotation(corr[0], corr[1], self.f[-1])  # cur -> prev: R_prev,cur
        self.r.append(r_pc.T @ prev_r)
        self.f.append(float(np.clip(self.f[-1] * z, self.f0 * 0.2, self.f0 * 8)))
        self.seg.append(self.seg[-1])

    def anchor(self, i: int, j: int, corr: Corr) -> None:
        """Frame i registered against frame j (pairs i -> j, centred px)."""
        rj = self.r[j]
        ri = self.r[i]
        if rj is None or ri is None or self.seg[j] not in self.placed:
            return
        guess = rj @ ri.T if self.seg[i] in self.placed else None
        r_ji, z, rms = fit_rotation(corr[0], corr[1], self.f[j], guess)
        if rms > 2.5:
            return
        target = r_ji.T @ rj
        f_new = self.f[j] * z
        seg = self.seg[i]
        if seg in self.placed:
            d = _angle(target, ri)
            if d > np.radians(4):  # implausible jump: keep the chain
                return
            self.corrections.append(float(np.degrees(d)))
            self.r[i], self.f[i] = target, f_new
            return
        # place the whole segment: same world offset for all its frames so far
        w = ri.T @ target
        scale = f_new / self.f[i]
        for k in range(len(self.r) - 1, -1, -1):
            if self.seg[k] != seg:
                break
            rk = self.r[k]
            if rk is not None:
                self.r[k] = rk @ w
                self.f[k] *= scale
        self.placed.add(seg)


def _centred(width: int, height: int) -> F64:
    return np.array([[1, 0, -width / 2], [0, 1, -height / 2], [0, 0, 1.0]])


class MotionEstimator:
    """Streaming estimator; feed frames in order, then call `finish`."""

    def __init__(
        self,
        work_width: int = 640,
        keyframe_every: int = 10,
        keep_every: int = 0,
        max_keyframes: int = 900,
        focal: float | None = None,
    ) -> None:
        self.work_width = work_width
        self.keyframe_every = keyframe_every
        self.keep_every = keep_every
        self.max_keyframes = max_keyframes
        self.focal = focal  # full-resolution px; estimated when None
        self.orb = cv2.ORB.create(nfeatures=1000, fastThreshold=10)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        self.keyframes: list[_Keyframe] = []
        self.steps: list[Corr | None] = []  # cur -> prev
        self.anchors: list[tuple[int, int, Corr]] = []  # (i, j, pairs i -> j)
        self.wide: list[tuple[int, int, Corr]] = []  # 8 to 30 degrees apart, for the focal length
        self.samples: list[tuple[int, U8]] = []
        self.size: tuple[int, int] | None = None
        self.work_size = (0, 0)
        self.centre = np.zeros(2)
        self.scale = 1.0
        self.prev: U8 | None = None
        self.prev_pts: NDArray[np.float32] | None = None
        self.poses: _Poses | None = None
        self.n = 0

    # --- registration helpers -----------------------------------------------------------

    def _inliers(self, src: NDArray[Any], dst: NDArray[Any], thr: float, min_n: int) -> Corr | None:
        h, inl = cv2.findHomography(src, dst, cv2.RANSAC, thr)
        if h is None or inl is None:
            return None
        keep = inl.ravel() == 1
        if keep.sum() < min_n or keep.sum() < 0.3 * len(src):
            return None
        s = src[keep].reshape(-1, 2).astype(np.float64) - self.centre
        d = dst[keep].reshape(-1, 2).astype(np.float64) - self.centre
        if len(s) > 250:
            idx = np.linspace(0, len(s) - 1, 250).astype(int)
            s, d = s[idx], d[idx]
        return s, d

    def _klt(self, grey: U8) -> Corr | None:
        """Point pairs current -> previous frame (centred work px), RANSAC inliers."""
        if self.prev is None or self.prev_pts is None or len(self.prev_pts) < 20:
            return None
        nxt, st, _ = cv2.calcOpticalFlowPyrLK(  # type: ignore[call-overload]
            self.prev, grey, self.prev_pts, None, winSize=(21, 21), maxLevel=3
        )
        if nxt is None:
            return None
        ok = st.ravel() == 1
        if ok.sum() < 20:
            return None
        return self._inliers(nxt[ok], self.prev_pts[ok], 1.5, 20)

    def _match(self, kp: NDArray[np.float32], desc: U8 | None, kf: _Keyframe) -> Corr | None:
        if desc is None or kf.desc is None or len(kp) < 30 or len(kf.kp) < 30:
            return None
        pairs = self.matcher.knnMatch(desc, kf.desc, k=2)
        good = [p[0] for p in pairs if len(p) == 2 and p[0].distance < 0.75 * p[1].distance]
        if len(good) < 30:
            return None
        src = kp[[m.queryIdx for m in good]]
        dst = kf.kp[[m.trainIdx for m in good]]
        return self._inliers(src, dst, 2.5, 35)

    def _keyframe(self, i: int, grey: U8) -> None:
        assert self.poses is not None
        kp_obj, desc = self.orb.detectAndCompute(grey, None)
        kp = np.array([k.pt for k in kp_obj], np.float32).reshape(-1, 2)
        poses = self.poses
        ri = poses.r[i]
        placed = poses.seg[i] in poses.placed
        cands = [
            k
            for k in self.keyframes
            if poses.seg[k.index] in poses.placed and (not placed or i - k.index > 60)
        ]
        if placed and ri is not None:
            cands = sorted(cands, key=lambda k: _angle(poses.r[k.index], ri))[:3]  # type: ignore[arg-type]
        elif cands:
            cands = cands[:: max(1, len(cands) // 16)]  # lost: try a spread of placed keyframes
        for kf in cands:
            corr = self._match(kp, desc, kf)
            if corr is not None:
                self.anchors.append((i, kf.index, corr))
                poses.anchor(i, kf.index, corr)
                break
        if (
            placed
            and ri is not None
            and len(self.wide) < 80
            and (i // self.keyframe_every) % 4 == 0
        ):
            far = [
                k
                for k in self.keyframes
                if poses.seg[k.index] in poses.placed
                and np.radians(8) < _angle(poses.r[k.index], ri) < np.radians(30)  # type: ignore[arg-type]
            ]
            for kf in sorted(far, key=lambda k: -_angle(poses.r[k.index], ri))[:2]:  # type: ignore[arg-type]
                corr = self._match(kp, desc, kf)
                if corr is not None:
                    self.wide.append((i, kf.index, corr))
                    break
        if desc is not None:
            if len(self.keyframes) >= self.max_keyframes:
                self.keyframes.pop(len(self.keyframes) // 2)
            self.keyframes.append(_Keyframe(i, kp, desc))

    # --- streaming ----------------------------------------------------------------------

    def add(self, frame: U8) -> None:
        if self.size is None:
            self.size = (frame.shape[1], frame.shape[0])
            self.scale = self.work_width / frame.shape[1]
            self.work_size = (self.work_width, round(frame.shape[0] * self.scale))
            self.centre = np.array([self.work_size[0] / 2, self.work_size[1] / 2])
            f0 = self.focal * self.scale if self.focal else float(self.work_width)
            self.poses = _Poses(f0)
        assert self.poses is not None
        small = cv2.resize(frame, self.work_size, interpolation=cv2.INTER_AREA)
        grey = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        i = self.n
        self.n += 1
        if self.keep_every and i % self.keep_every == 0:
            self.samples.append((i, frame.copy()))
        corr = self._klt(grey) if i else None
        self.steps.append(corr)
        self.poses.step(corr)
        if i % self.keyframe_every == 0 or corr is None:
            self._keyframe(i, grey)
        self.prev = grey
        pts = cv2.goodFeaturesToTrack(grey, maxCorners=400, qualityLevel=0.01, minDistance=8)
        self.prev_pts = None if pts is None else pts.astype(np.float32)

    def finish(self, max_canvas_width: int = 3600) -> CameraMotion:
        assert self.size is not None and self.poses is not None, "no frames"
        if self.focal:
            f = self.focal * self.scale
        else:  # anchors with the largest rotation constrain the focal length best
            online = self.poses

            def turn(a: tuple[int, int, Corr]) -> float:
                ri, rj = online.r[a[0]], online.r[a[1]]
                return 0.0 if ri is None or rj is None else _angle(ri, rj)

            pairs = self.wide + sorted(self.anchors, key=turn, reverse=True)[:20]
            zooms = [online.f[j] / online.f[0] for _, j, _ in pairs]
            f = estimate_focal([c for _, _, c in pairs], float(self.work_width), zooms)
        poses = _Poses(f)  # replay with the estimated focal length
        by_frame: dict[int, list[tuple[int, Corr]]] = {}
        for i, j, c in self.anchors:
            by_frame.setdefault(i, []).append((j, c))
        for i, corr in enumerate(self.steps):
            poses.step(corr)
            for j, ca in by_frame.get(i, []):
                poses.anchor(i, j, ca)
        stats = {
            "frames": float(self.n),
            "focal_px": f / self.scale,
            "cuts": float(sum(c is None for c in self.steps[1:])),
            "anchors": float(len(self.anchors)),
            "mean_correction_deg": float(np.mean(poses.corrections)) if poses.corrections else 0.0,
        }
        return _canvas(self.size, self.scale, poses, self.samples, stats, max_canvas_width)


def _canvas(
    size: tuple[int, int],
    scale: float,
    poses: _Poses,
    samples: list[tuple[int, U8]],
    stats: dict[str, float],
    max_canvas_width: int,
) -> CameraMotion:
    """Reference view and canvas; focal lengths converted to full-resolution pixels."""
    w, h = size
    n = len(poses.r)
    rots: list[F64 | None] = [
        poses.r[i] if poses.r[i] is not None and poses.seg[i] in poses.placed else None
        for i in range(n)
    ]
    focals = [f / scale for f in poses.f]
    valid = [i for i in range(n) if rots[i] is not None]
    stats["coverage"] = len(valid) / n if n else 0.0
    if not valid:
        return CameraMotion(size, False, rots, focals, samples=samples, stats=stats)
    axes = np.array([_axis(rots[i]) for i in valid])  # type: ignore[arg-type]
    pan = np.arctan2(axes[:, 0], axes[:, 2])
    tilt = np.arcsin(np.clip(axes[:, 1], -1, 1))
    zoom = np.array([focals[i] for i in valid])
    stats["pan_deg"] = float(np.degrees(np.percentile(pan, 98) - np.percentile(pan, 2)))
    stats["zoom_ratio"] = float(np.percentile(zoom, 98) / np.percentile(zoom, 2))
    if stats["pan_deg"] < 1.0 and stats["zoom_ratio"] < 1.03:
        eye = np.eye(3)
        fixed = CameraMotion.fixed(size, n)
        fixed.rotations = [eye if r is not None else None for r in rots]
        fixed.samples, fixed.stats = samples, stats
        return fixed
    # reference: middle of the pan range (the court is usually centred in it), median tilt
    mid_pan = (np.percentile(pan, 2) + np.percentile(pan, 98)) / 2
    ref = valid[int(np.argmin(np.abs(pan - mid_pan) + np.abs(tilt - np.median(tilt))))]
    ref_r = rots[ref]
    assert ref_r is not None
    # canvas extent: directions seen by the frames, limited to MAX_VIEW_ANGLE around the axis
    gx, gy = np.meshgrid(np.linspace(0, w, 7), np.linspace(0, h, 5))
    grid = np.stack([gx.ravel() - w / 2, gy.ravel() - h / 2, np.ones(gx.size)], axis=1)
    pts = []
    for i in valid[:: max(1, len(valid) // 400)]:
        ri = rots[i]
        assert ri is not None
        rays = (grid / np.array([focals[i], focals[i], 1.0])) @ ri  # world
        cam = rays @ ref_r.T
        ok = cam[:, 2] > np.cos(MAX_VIEW_ANGLE) * np.linalg.norm(cam, axis=1)
        pts.append(cam[ok, :2] / cam[ok, 2:3])
    uv = np.vstack(pts)  # normalised canvas coordinates (tan of angle)
    lo = np.percentile(uv, 0.5, axis=0)
    hi = np.percentile(uv, 99.5, axis=0)
    f_ref = float(np.median(zoom))
    span = (hi - lo) * f_ref
    k = min(1.0, max_canvas_width / max(span[0], 1.0), (max_canvas_width * 0.6) / max(span[1], 1.0))
    canvas_f = f_ref * k
    canvas_c = (float(-lo[0] * canvas_f), float(-lo[1] * canvas_f))
    stats["canvas_scale"] = float(k)
    return CameraMotion(
        size,
        True,
        rots,
        focals,
        ref_r=ref_r,
        canvas_f=canvas_f,
        canvas_c=canvas_c,
        canvas_size=(int(np.ceil(span[0] * k)), int(np.ceil(span[1] * k))),
        samples=samples,
        stats=stats,
    )


def estimate_motion(
    frames: Iterable[U8], keep_samples: int = 30, expected_frames: int = 0, **kwargs: Any
) -> CameraMotion:
    keep_every = max(1, expected_frames // keep_samples) if expected_frames else 25
    est = MotionEstimator(keep_every=keep_every, **kwargs)
    for f in frames:
        est.add(f)
    motion = est.finish()
    if len(motion.samples) > keep_samples:
        step = len(motion.samples) / keep_samples
        motion.samples = [motion.samples[int(k * step)] for k in range(keep_samples)]
    return motion

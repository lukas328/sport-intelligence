import { toImage, type Pt } from "./court-calibration";
import type { Homography } from "./spotlight";

/** The four court corners in metres, in the order the handles are named. */
export const CORNERS: readonly Pt[] = [
  [0, 0],
  [40, 0],
  [40, 20],
  [0, 20],
];
export const CORNER_NAMES = ["cornerNearLeft", "cornerNearRight", "cornerFarRight", "cornerFarLeft"] as const;

/**
 * Where the four corners sit in the hall image: the stored court projected back into the
 * panorama (court to image), or a frame inside the image when there is no court in that space.
 */
export function cornersOf(h: Homography | null | undefined, size: [number, number]): Pt[] {
  const [w, hgt] = size;
  const proj = h ? CORNERS.map((c) => toImage(h, c)) : [];
  if (proj.length === 4 && proj.every(Boolean)) return proj as Pt[];
  return [
    [w * 0.1, hgt * 0.8],
    [w * 0.9, hgt * 0.8],
    [w * 0.8, hgt * 0.3],
    [w * 0.2, hgt * 0.3],
  ];
}

/**
 * Where a corner's handle is drawn: the corner itself inside the picture, else the point where
 * the line from the court's middle to it leaves the picture (E04: every handle reachable).
 */
export function handleAt(corner: Pt, corners: Pt[], w: number, h: number): Pt {
  const [x, y] = corner;
  if (x >= 0 && x <= w && y >= 0 && y <= h) return corner;
  const cx = corners.reduce((a, c) => a + c[0], 0) / corners.length;
  const cy = corners.reduce((a, c) => a + c[1], 0) / corners.length;
  if (!(cx >= 0 && cx <= w && cy >= 0 && cy <= h))
    return [Math.min(w, Math.max(0, x)), Math.min(h, Math.max(0, y))];
  let t = 1;
  const dx = x - cx;
  const dy = y - cy;
  if (dx > 0) t = Math.min(t, (w - cx) / dx);
  if (dx < 0) t = Math.min(t, (0 - cx) / dx);
  if (dy > 0) t = Math.min(t, (h - cy) / dy);
  if (dy < 0) t = Math.min(t, (0 - cy) / dy);
  return [cx + dx * t, cy + dy * t];
}

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


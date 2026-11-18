/**
 * The camera of the drawn hall image of the calibration component page (app/dev/kalibrierung,
 * draw-hall.ts) and its tests: a camera on the near side looking at the whole court. Invented,
 * no real hall. No imports beyond types: the e2e tests load it in Node as it is.
 */
import type { Homography } from "@/lib/spotlight";

export const HALL_SIZE: [number, number] = [1280, 720];

/** Court metres -> image pixels of the drawn hall (camera at the near sideline, raised). */
export const HALL_H: Homography = [
  [30, 16, 40],
  [0, -13.75, 650],
  [0, 0.025, 1],
];

/** The automatic suggestion of the page: a little off, as a wrong automatic court looks. */
export const HALL_H_OFF: Homography = [
  [29.2, 17.5, 62],
  [0.4, -13.1, 628],
  [0, 0.0262, 1],
];

export function project(h: Homography, x: number, y: number): [number, number] {
  const w = h[2]![0]! * x + h[2]![1]! * y + h[2]![2]!;
  return [(h[0]![0]! * x + h[0]![1]! * y + h[0]![2]!) / w, (h[1]![0]! * x + h[1]![1]! * y + h[1]![2]!) / w];
}

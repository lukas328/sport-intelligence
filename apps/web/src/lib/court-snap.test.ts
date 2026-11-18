import { describe, expect, it } from "vitest";
import { lineMask, snapMargin, snapToLine, type Pixels } from "./court-snap";

type RGB = [number, number, number];

/** A synthetic hall floor with painted lines and a little grain. */
function floor(w: number, h: number, base: RGB, paint: (x: number, y: number) => RGB | null): Pixels {
  const data = new Uint8ClampedArray(w * h * 4);
  let s = 3;
  const grain = () => ((s = (s * 16807) % 2147483647) / 2147483647 - 0.5) * 16;
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const c = paint(x, y) ?? base;
      const i = (y * w + x) * 4;
      const g = grain();
      data[i] = c[0] + g;
      data[i + 1] = c[1] + g;
      data[i + 2] = c[2] + g;
      data[i + 3] = 255;
    }
  return { data, width: w, height: h };
}

const WOOD: RGB = [196, 160, 112];
const DARK: RGB = [70, 72, 76];

describe("snapping a click onto the court line", () => {
  it("moves a click beside a white line to the middle of the line", () => {
    const img = floor(120, 80, DARK, (_, y) => (y >= 40 && y <= 42 ? [235, 235, 235] : null));
    const [x, y] = snapToLine(img, [60, 47], 10);
    expect(x).toBeCloseTo(60, 0);
    expect(Math.abs(y - 41)).toBeLessThan(0.6);
  });

  it("finds a coloured line that is darker than a wooden floor", () => {
    const img = floor(120, 80, WOOD, (x) => (x >= 70 && x <= 71 ? [30, 70, 170] : null));
    const [x, y] = snapToLine(img, [64, 30], 10);
    expect(Math.abs(x - 70.5)).toBeLessThan(0.6);
    expect(y).toBeCloseTo(30, 0);
  });

  it("leaves the click where it is when no line is near", () => {
    const img = floor(120, 80, WOOD, (x) => (x === 10 ? [255, 255, 255] : null));
    expect(snapToLine(img, [80, 40], 10)).toEqual([80, 40]);
    // the grain of the floor alone is no line
    expect(lineMask(floor(60, 40, WOOD, () => null)).every((v) => v === 0)).toBe(true);
  });

  it("takes the nearer of two lines and works on a cut-out of the image", () => {
    const full = floor(200, 100, DARK, (x) => (x === 90 || x === 104 ? [240, 240, 240] : null));
    const p: [number, number] = [101, 50];
    const m = snapMargin(10);
    const [x0, y0] = [p[0] - m, p[1] - m];
    const w = 2 * m + 1;
    const data = new Uint8ClampedArray(w * w * 4);
    for (let y = 0; y < w; y++) for (let x = 0; x < w; x++) for (let c = 0; c < 4; c++) data[(y * w + x) * 4 + c] = full.data[((y0 + y) * 200 + x0 + x) * 4 + c]!;
    const [x] = snapToLine({ data, width: w, height: w, x0, y0 }, p, 10);
    expect(Math.abs(x - 104)).toBeLessThan(0.6);
  });
});

import { describe, expect, it } from "vitest";
import { boxOnCanvas, cropView, nearestTrack, positionAt, project, trackSamples, trail } from "./spotlight";

const H = [
  [32, 0, 0],
  [0, 36, 0],
  [0, 0, 1],
]; // 40 m -> 1280 px, 20 m -> 720 px

describe("spotlight", () => {
  it("projects court metres into the picture", () => {
    expect(project(H, 20, 10, [1280, 720])).toEqual([0.5, 0.5]);
  });

  it("interpolates and fades out after a track loss", () => {
    const s = [
      { t: 0, x: 0, y: 0 },
      { t: 200, x: 2, y: 0 },
      { t: 1500, x: 4, y: 0 },
    ];
    expect(positionAt(s, 100)).toEqual({ x: 1, y: 0, alpha: 1 });
    expect(positionAt(s, 300)?.alpha).toBe(1);
    const fading = positionAt(s, 500)!;
    expect(fading.alpha).toBeGreaterThan(0);
    expect(fading.alpha).toBeLessThan(1);
    expect(fading.x).toBe(2); // no jump towards the next sample
    expect(positionAt(s, 900)).toBeNull();
    expect(positionAt(s, 1400)?.alpha).toBeCloseTo(2 / 3, 5);
    expect(trail(s, 1500, 1400).map((p) => p.t)).toEqual([200, 1500]);
  });

  it("keeps the box on the person at every canvas size and video shape (L5)", () => {
    const box = { x: 0.4, y: 0.3, w: 0.05, h: 0.2 };
    // the box's centre in video pixels must land where the box is drawn on the canvas
    for (const [vw, vh] of [
      [1280, 720],
      [960, 720],
      [720, 1280],
    ] as const) {
      for (const [W, H] of [
        [390, 219],
        [1280, 720],
        [800, 800],
      ] as const) {
        const v = cropView(box, vw, vh, W, H);
        // never stretched: the crop has the canvas's aspect, or it is letterboxed
        expect(v.dw / v.dh).toBeCloseTo(v.sw / v.sh, 5);
        expect(v.dx).toBeGreaterThanOrEqual(-1e-6);
        expect(v.dy).toBeGreaterThanOrEqual(-1e-6);
        // the crop lies inside the frame
        expect(v.sx).toBeGreaterThanOrEqual(0);
        expect(v.sy).toBeGreaterThanOrEqual(0);
        expect(v.sx + v.sw).toBeLessThanOrEqual(vw + 1e-6);
        expect(v.sy + v.sh).toBeLessThanOrEqual(vh + 1e-6);
        const b = boxOnCanvas(box, vw, vh, v);
        const cx = (box.x + box.w / 2) * vw;
        const cy = (box.y + box.h / 2) * vh;
        expect(b.x + b.w / 2).toBeCloseTo(v.dx + (cx - v.sx) * v.scale, 5);
        expect(b.y + b.h / 2).toBeCloseTo(v.dy + (cy - v.sy) * v.scale, 5);
        expect(b.w / b.h).toBeCloseTo((box.w * vw) / (box.h * vh), 5);
      }
    }
  });

  it("shows the whole frame letterboxed without a box", () => {
    const v = cropView(null, 720, 1280, 1280, 720);
    expect(v.sw).toBe(720);
    expect(v.dh).toBeCloseTo(720, 5);
    expect(v.dw).toBeCloseTo(405, 5);
    expect(v.dx).toBeCloseTo((1280 - 405) / 2, 5);
  });

  it("finds the clicked player", () => {
    const rows = new Float32Array([1000, 3, 20, 10, 1000, 4, 5, 5, 1000, 3, 21, 10]);
    expect(trackSamples(rows, 3).length).toBe(2);
    expect(nearestTrack(rows, 1000, H, [1280, 720], [0.5, 0.5])).toBe(3);
    expect(nearestTrack(rows, 1000, H, [1280, 720], [0.9, 0.9])).toBeNull();
  });
});

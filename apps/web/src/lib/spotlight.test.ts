import { describe, expect, it } from "vitest";
import { nearestTrack, positionAt, project, trackSamples, trail } from "./spotlight";

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

  it("finds the clicked player", () => {
    const rows = new Float32Array([1000, 3, 20, 10, 1000, 4, 5, 5, 1000, 3, 21, 10]);
    expect(trackSamples(rows, 3).length).toBe(2);
    expect(nearestTrack(rows, 1000, H, [1280, 720], [0.5, 0.5])).toBe(3);
    expect(nearestTrack(rows, 1000, H, [1280, 720], [0.9, 0.9])).toBeNull();
  });
});

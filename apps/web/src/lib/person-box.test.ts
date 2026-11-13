import { describe, expect, it } from "vitest";
import { personBox, project } from "./spotlight";

// 20 px per court metre, court origin at (100, 50): a plain scaling as homography
const H = [
  [20, 0, 100],
  [0, 20, 50],
  [0, 0, 1],
];
const SIZE: [number, number] = [1280, 720];

describe("personBox", () => {
  it("stands on the foot point with the body height at the image scale there", () => {
    const b = personBox(H, 10, 10, SIZE)!;
    const foot = project(H, 10, 10, SIZE)!;
    expect(b.y + b.h).toBeCloseTo(foot[1]);
    expect(b.x + b.w / 2).toBeCloseTo(foot[0]);
    expect(b.h * SIZE[1]).toBeCloseTo(1.85 * 20);
    expect(b.w * SIZE[0]).toBeCloseTo(0.8 * 20);
  });
  it("is smaller far away under a perspective homography", () => {
    // depth: w grows with y, so points further up the court are drawn smaller
    const P = [
      [20, 0, 100],
      [0, 20, 50],
      [0, 0.05, 1],
    ];
    const near = personBox(P, 10, 2, SIZE)!;
    const far = personBox(P, 10, 30, SIZE)!;
    expect(far.h).toBeLessThan(near.h);
  });
  it("has no box where the homography is degenerate", () => {
    expect(personBox([[0, 0, 0], [0, 0, 0], [0, 0, 0]], 1, 1, SIZE)).toBeNull();
  });
});

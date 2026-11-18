import { describe, expect, it } from "vitest";
import { ballWay } from "@/lib/ball-way";

describe("the ball's way through the steps", () => {
  it("runs from ball to ball, each leg leaving straight down and arriving from straight above", () => {
    expect(ballWay([])).toBe("");
    expect(ballWay([[10, 0]])).toBe("M10.0 0.0");
    expect(
      ballWay([
        [100, 50],
        [300, 250],
        [120, 650],
      ]),
    ).toBe("M100.0 50.0C100.0 150.0 300.0 150.0 300.0 250.0C300.0 450.0 120.0 450.0 120.0 650.0");
  });

  it("only ever runs down: the heights of all its points never go back up", () => {
    const pts = [
      [500, 120],
      [700, 900],
      [400, 1700],
      [800, 2600],
    ] as const;
    const d = ballWay(pts);
    // per leg: start, two control points, end; all heights in order
    const ys = [...d.matchAll(/(-?\d+\.\d) (-?\d+\.\d)/g)].map((m) => Number(m[2]));
    for (let i = 1; i < ys.length; i++) expect(ys[i]!).toBeGreaterThanOrEqual(ys[i - 1]!);
  });
});

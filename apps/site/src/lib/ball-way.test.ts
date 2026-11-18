import { describe, expect, it } from "vitest";
import { ballWay, ballY } from "@/lib/ball-way";

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

describe("where the ball is while scrolling", () => {
  const rows = [400, 1200, 2000];
  const pts = [
    [500, 300],
    [300, 1250],
    [700, 1900],
  ] as const;

  it("sits on a step's ball while that step's row is in the middle of the screen", () => {
    expect(ballY(rows, pts, 400)).toBe(300);
    expect(ballY(rows, pts, 1200)).toBe(1250);
    expect(ballY(rows, pts, 2000)).toBe(1900);
  });

  it("runs in proportion between two steps and waits at the first and the last ball", () => {
    expect(ballY(rows, pts, 800)).toBe(775);
    expect(ballY(rows, pts, 0)).toBe(300);
    expect(ballY(rows, pts, 5000)).toBe(1900);
    expect(ballY([], [], 42)).toBe(42);
  });
});

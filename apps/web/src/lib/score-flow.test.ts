import { describe, expect, it } from "vitest";
import { scoreFlow } from "./score-flow";

const at = (own: number, opp: number, clock_s = 60) => ({ clock_s, own, opp });

describe("the run of the match as one difference line (A14)", () => {
  it("is the difference, ours up", () => {
    expect(scoreFlow([at(0, 0, 0), at(1, 0), at(1, 2), at(4, 2)]).diffs).toEqual([0, 1, -1, 2]);
  });

  it("keeps the middle in the middle: the scale is the same both ways, at least three goals", () => {
    const { top, grid } = scoreFlow([at(0, 0, 0), at(1, 0)]);
    expect(top).toBe(3);
    expect(grid).toEqual([3, 2, 1, 0, -1, -2, -3]);
  });

  it("uses coarser steps for a clear result", () => {
    const { top, grid } = scoreFlow([at(0, 0, 0), at(0, 7)]);
    expect(top).toBe(8);
    expect(grid).toEqual([8, 6, 4, 2, 0, -2, -4, -6, -8]);
    expect(scoreFlow([at(0, 0, 0), at(14, 1)]).grid[0]).toBe(15);
  });
});

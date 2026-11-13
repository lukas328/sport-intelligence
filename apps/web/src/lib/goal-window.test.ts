import { describe, expect, it } from "vitest";
import { goalWindow, sameGoal } from "./goal-window";

describe("goal questions (real-video test G2)", () => {
  it("shows about 10 s before the candidate time to 2 s after", () => {
    expect(goalWindow({ t_ms: 135_000 })).toEqual({ start_ms: 125_000, end_ms: 137_000 });
    expect(goalWindow({ t_ms: 4_000 })).toEqual({ start_ms: 0, end_ms: 6_000 });
  });
  it("names the goal at 2:06 already confirmed for the same side in the clip at 2:15", () => {
    const goals = [
      { team: "own", t_ms: 126_000, has_video: true },
      { team: "opp", t_ms: 153_000, has_video: true },
    ];
    expect(sameGoal(goals, { t_ms: 135_000, suggested_side: "own" })?.t_ms).toBe(126_000);
    // the other side, or a goal outside the clip: no hint
    expect(sameGoal(goals, { t_ms: 135_000, suggested_side: "opponent" })).toBeNull();
    expect(sameGoal(goals, { t_ms: 200_000, suggested_side: "own" })).toBeNull();
    // without a suggestion any side counts
    expect(sameGoal(goals, { t_ms: 162_000, suggested_side: null })?.t_ms).toBe(153_000);
  });
});

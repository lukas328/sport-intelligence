import { describe, expect, it } from "vitest";
import { COURT, distanceToAttackedGoal, normalizeToAttack } from "./index";

describe("court", () => {
  it("has handball dimensions", () => {
    expect(COURT.length).toBe(40);
    expect(COURT.width).toBe(20);
    expect(COURT.keypoints["post_right_low"]).toEqual([40, 8.5]);
  });

  it("normalises attack direction", () => {
    expect(normalizeToAttack([5, 3], false)).toEqual([35, 17]);
    expect(normalizeToAttack([5, 3], true)).toEqual([5, 3]);
  });

  it("computes distance to goal", () => {
    expect(distanceToAttackedGoal([33, 10])).toBeCloseTo(7);
    for (const p of COURT.lines["goal_area_right"] ?? []) {
      expect(distanceToAttackedGoal(p)).toBeCloseTo(6, 2);
    }
  });
});

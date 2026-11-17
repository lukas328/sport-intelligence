import { describe, expect, it } from "vitest";
import { goalDistance, SHOT_MIN } from "@/lib/demo";
import { saturday, threeMatchesLater } from "./story";

describe("the start page's week", () => {
  it("starts with the demo match: lost 16:18, 9 of 18 over the right wing", () => {
    const s = saturday();
    expect(s.score).toBe("16:18");
    expect([s.n, s.of, s.zone]).toEqual([9, 18, "ra"]);
    expect(s.dots).toHaveLength(18);
    expect(s.dots.filter((d) => d.ra)).toHaveLength(9);
  });

  it("ends three matches later with 3 of 22, the three on the right wing", () => {
    const l = threeMatchesLater();
    expect([l.n, l.of]).toEqual([3, 22]);
    for (const d of l.dots.filter((x) => x.ra)) expect(d.at[0]).toBeGreaterThan(16);
    for (const d of l.dots) {
      expect(goalDistance(d.at)).toBeGreaterThanOrEqual(SHOT_MIN - 1e-9);
      expect(d.at[0]).toBeGreaterThanOrEqual(0);
      expect(d.at[0]).toBeLessThanOrEqual(20);
    }
  });
});

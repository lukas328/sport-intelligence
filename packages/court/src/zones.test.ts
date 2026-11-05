import { describe, expect, it } from "vitest";
import cases from "../spec/zone_cases.json";
import { mirrorGoalZone, shotZone } from "./zones";

describe("shot zones", () => {
  it.each(cases.cases)("($x, $y) -> $zone", (c) => {
    expect(shotZone(c.x, c.y, { penalty: "penalty" in c, fastBreak: "fast_break" in c, emptyGoal: "empty_goal" in c })).toBe(c.zone);
  });
  it("mirrors goal zones", () => {
    expect(mirrorGoalZone("TL")).toBe("TR");
    expect(mirrorGoalZone("BC")).toBe("BC");
  });
});

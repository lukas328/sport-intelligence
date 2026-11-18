import { describe, expect, it } from "vitest";
import { nextHidden } from "./header-scroll";

describe("the pinned bar on the phone (BEFUNDE-3 U12)", () => {
  const bar = 66;
  it("stays near the top of the page", () => {
    expect(nextHidden(false, 40, 30, bar)).toBe(false);
    expect(nextHidden(true, bar, 30, bar)).toBe(false);
  });
  it("goes while scrolling down and comes back on the first step up", () => {
    expect(nextHidden(false, 600, 40, bar)).toBe(true);
    expect(nextHidden(true, 590, -1, bar)).toBe(false);
  });
  it("ignores a little downward jitter either way", () => {
    expect(nextHidden(false, 600, 3, bar)).toBe(false);
    expect(nextHidden(true, 600, 3, bar)).toBe(true);
    expect(nextHidden(true, 600, 0, bar)).toBe(true);
  });
});

import { describe, expect, it } from "vitest";
import { deltaE, hexToLab, kitWarnings } from "./kit";

describe("kit colours", () => {
  it("converts to CIELAB", () => {
    const [l, a, b] = hexToLab("#ffffff");
    expect(l).toBeCloseTo(100, 0);
    expect(Math.abs(a)).toBeLessThan(0.5);
    expect(Math.abs(b)).toBeLessThan(0.5);
    expect(hexToLab("#000000")[0]).toBeCloseTo(0, 5);
  });

  it("flags similar kits like the API", () => {
    expect(deltaE("#c8102e", "#d0142f")).toBeLessThan(5);
    expect(kitWarnings({ own: "#0b6bcb", own_gk: "#f59e0b", opponent: "#dc2626", opponent_gk: "#16a34a" })).toEqual([]);
    expect(kitWarnings({ own: "#c8102e", own_gk: "#f59e0b", opponent: "#d0142f", opponent_gk: "#16a34a" })).toEqual([
      ["own", "opponent"],
    ]);
  });
});

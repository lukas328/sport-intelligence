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

  it("checks the referee kit against both field kits only when it is known", () => {
    const teams = { own: "#0b6bcb", own_gk: "#f59e0b", opponent: "#1a1a1a", opponent_gk: "#16a34a" };
    expect(kitWarnings({ ...teams, referee: null })).toEqual([]);
    expect(kitWarnings({ ...teams, referee: "#111111" })).toEqual([["opponent", "referee"]]);
    expect(kitWarnings({ ...teams, referee: "#ff6a13" })).toEqual([]);
    // a referee close to a goalkeeper kit is not a warning (the API checks the same pairs)
    expect(kitWarnings({ ...teams, referee: "#f59e0b" })).toEqual([]);
  });
});

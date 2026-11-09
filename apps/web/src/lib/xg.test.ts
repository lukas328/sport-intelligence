import { describe, expect, it } from "vitest";
import { xgBasis } from "./xg";

describe("xG basis", () => {
  it("shows xG when most shots on target have a position", () => {
    expect(xgBasis({ xg: 12.3, xg_shots: 18, xg_coverage: 0.9 })).toEqual({ shown: true });
  });
  it("says how many shots have a position when too few do", () => {
    expect(xgBasis({ xg: 1.2, xg_shots: 3, xg_coverage: 0.1 })).toEqual({ shown: false, n: 3, of: 30 });
  });
  it("says nothing without shots on target", () => {
    expect(xgBasis({ xg: 0, xg_shots: 0, xg_coverage: null })).toBeNull();
  });
});

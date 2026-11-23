import { describe, expect, it } from "vitest";
import { roundCandidate } from "./check-round";

const list = [
  { id: "a", status: "confirmed" },
  { id: "b", status: "open" },
  { id: "c", status: "rejected" },
];

describe("roundCandidate", () => {
  it("asks an open moment", () => {
    expect(roundCandidate(list, "b", [])?.id).toBe("b");
  });
  it("keeps a moment answered in this round, so the count does not jump", () => {
    expect(roundCandidate(list, "a", ["a"])?.id).toBe("a");
    expect(roundCandidate(list, "c", new Set(["c"]))?.id).toBe("c");
  });
  it("drops a moment answered elsewhere or gone", () => {
    expect(roundCandidate(list, "a", [])).toBeUndefined();
    expect(roundCandidate(list, "x", ["x"])).toBeUndefined();
    expect(roundCandidate(undefined, "b", [])).toBeUndefined();
  });
});

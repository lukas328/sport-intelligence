import { describe, expect, it } from "vitest";
import { freshMatch } from "./fresh-match";

const now = Date.parse("2026-11-13T12:00:00Z");
const at = (days: number) => new Date(now - days * 86_400_000).toISOString();

describe("freshMatch", () => {
  it("puts a fresh analysis in the head until it is opened", () => {
    const infos = [
      { id: "old", analysis: "ready", analysisAt: at(30), checks: 0 },
      { id: "new", analysis: "ready", analysisAt: at(0.1), checks: 0 },
    ];
    expect(freshMatch(infos, new Set(), now)).toBe("new");
    expect(freshMatch(infos, new Set(["new"]), now)).toBeNull();
  });
  it("keeps a match with open questions in the head, also once opened", () => {
    expect(freshMatch([{ id: "q", analysis: "ready", analysisAt: at(1), checks: 9 }], new Set(["q"]), now)).toBe("q");
  });
  it("ignores running and old analyses", () => {
    expect(freshMatch([{ id: "r", analysis: "running", analysisAt: null, checks: 0 }], new Set(), now)).toBeNull();
    expect(freshMatch([{ id: "o", analysis: "ready", analysisAt: at(8), checks: 3 }], new Set(), now)).toBeNull();
  });
});

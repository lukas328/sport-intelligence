import { describe, expect, it } from "vitest";
import data from "../../public/demo/match.json";
import { demoFigures, filterShots, isShot, type DemoMatch } from "./demo";

const match = data as unknown as DemoMatch;

describe("demo match", () => {
  it("is marked as fictional", () => {
    expect(match.fictional).toBe(true);
  });

  it("filters shots by side, outcome and half", () => {
    const all = match.events.filter(isShot);
    const own = filterShots(match, { side: "own", outcome: "all", period: 0 });
    const opp = filterShots(match, { side: "opponent", outcome: "all", period: 0 });
    expect(own.length + opp.length).toBe(all.length);
    const goals = filterShots(match, { side: "own", outcome: "goal", period: 0 });
    expect(goals.length).toBe(match.stats.own.goals);
    const first = filterShots(match, { side: "both", outcome: "all", period: 1 });
    expect(first.every((s) => s.period === 1)).toBe(true);
  });

  it("keeps every shot on the court and the score consistent", () => {
    for (const s of match.events.filter(isShot)) {
      expect(s.x).toBeGreaterThanOrEqual(0);
      expect(s.x).toBeLessThanOrEqual(40);
      expect(s.y).toBeGreaterThanOrEqual(0);
      expect(s.y).toBeLessThanOrEqual(20);
    }
    const goals = demoFigures(match).find(([k]) => k === "goals");
    expect(goals?.[1]).toBe(match.stats.timeline.final.own);
    expect(goals?.[2]).toBe(match.stats.timeline.final.opp);
  });
});

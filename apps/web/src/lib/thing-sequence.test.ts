import { describe, expect, it } from "vitest";
import { goalRuns, thingSequence, type MatchGraphics } from "./graphics";
import { threeThings } from "./three-things";

// a match: nine goals conceded over the right wing among others, all with a video time
const goal = (i: number, team: "own" | "opp", zone: string, tMs: number | null = i * 60_000) => ({
  event_id: `e${i}`,
  team,
  minute: i,
  run: [[30, 10] as [number, number], [36, 12] as [number, number]],
  shot: [36, 12] as [number, number],
  aim: null,
  confirmed: true,
  zone,
  spot_by_coach: true,
  t_ms: tMs,
  has_video: true,
  source: "video",
});
const goals = [
  ...Array.from({ length: 9 }, (_, i) => goal(i * 3 + 1, "opp", "ra")),
  goal(2, "own", "kr"),
  goal(5, "opp", "gs"),
  goal(8, "own", "kr"),
  goal(11, "own", "kr"),
  goal(14, "opp", "rl"),
];
const g = { goals, report_goals: [], field_confirmed: true, phases: [], checks: [] } as unknown as MatchGraphics;

describe("thingSequence (B01)", () => {
  it("holds exactly the scenes of the thing, in match order", () => {
    const things = threeThings(goalRuns(g));
    expect(things[0]?.key).toBe("conceded_zone");
    const seq = thingSequence(g, 1, things);
    expect(seq).toHaveLength(9);
    expect(seq.every((x) => x.team === "opp" && x.zone === "ra")).toBe(true);
    expect(seq.map((x) => x.t_ms)).toEqual([...seq.map((x) => x.t_ms)].sort((a, b) => (a ?? 0) - (b ?? 0)));
  });
  it("leaves out goals without a video time and unknown things", () => {
    const g2 = { ...g, goals: g.goals.map((x, i) => (i === 0 ? { ...x, t_ms: null } : x)) } as MatchGraphics;
    const things = threeThings(goalRuns(g2));
    expect(thingSequence(g2, 1, things)).toHaveLength(8);
    expect(thingSequence(g2, 3, things)).toEqual([]);
  });
});

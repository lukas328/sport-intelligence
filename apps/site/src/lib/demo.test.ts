import { describe, expect, it } from "vitest";
import data from "../../public/demo/match.json";
import de from "@/messages/de";
import { demoFigures, demoGoals, demoScene, demoThings, halfSpot, reportGoals, zoneOf, type DemoMatch } from "./demo";
import { demoView } from "./things";

const match = data as unknown as DemoMatch;

describe("demo match", () => {
  it("is marked as fictional", () => {
    expect(match.fictional).toBe(true);
  });

  it("takes every goal of the match, consistent with the final score", () => {
    const goals = demoGoals(match);
    expect(goals.filter((g) => g.team === "own")).toHaveLength(match.stats.timeline.final.own);
    expect(goals.filter((g) => g.team === "opp")).toHaveLength(match.stats.timeline.final.opp);
    expect(reportGoals(goals)).toHaveLength(goals.length);
  });

  it("keeps runs and shot spots on the half court and ends each run at its shot spot", () => {
    for (const g of demoGoals(match)) {
      for (const [u, v] of [...g.run, g.shot]) {
        expect(u).toBeGreaterThanOrEqual(0);
        expect(u).toBeLessThanOrEqual(20);
        expect(v).toBeGreaterThanOrEqual(0);
        expect(v).toBeLessThanOrEqual(20);
      }
      expect(g.run.at(-1)).toEqual(g.shot);
    }
  });

  it("names zones from the attacker's view (goal at the top, right is right)", () => {
    expect(zoneOf("jump_shot", halfSpot(31, 4))).toBe("rr");
    expect(zoneOf("jump_shot", halfSpot(31, 16))).toBe("rl");
    expect(zoneOf("wing", halfSpot(38, 19))).toBe("la");
    expect(zoneOf("penalty", halfSpot(33, 10))).toBe("m7");
  });

  it("computes the three things from the data, not by hand", () => {
    const t = demoThings(match);
    expect(t.against.n).toBe(t.against.goals.length);
    expect(t.against.total).toBe(match.stats.opponent.goals);
    expect(["m7", "gs"]).not.toContain(t.against.zone);
    expect(t.fastBreak.n).toBe(match.stats.own.fast_break_goals);
    expect(t.turnovers.n).toBe(match.stats.own.turnovers);
    expect(t.turnovers.window.n).toBeGreaterThan(1);
  });

  it("draws no ball in the scene: the analysis does not find it yet", () => {
    const t = demoThings(match);
    const scene = demoScene(t.against.goals[0]!, "x");
    expect(scene.ball).toEqual([]);
    expect(scene.tracks.filter((x) => x.team === "own")).toHaveLength(7);
    expect(scene.tracks.filter((x) => x.team === "opp")).toHaveLength(6);
  });

  it("gives every figure a source and the match's own numbers", () => {
    const f = demoFigures(match);
    expect(f.find((x) => x.key === "goals")).toMatchObject({ own: 25, opp: 24, source: "report" });
    expect(f.find((x) => x.key === "saves")?.source).toBe("marked");
  });

  it("fills in the texts without leftover placeholders", () => {
    const v = demoView(de);
    for (const t of v.things) for (const s of [t.index, t.unit, t.text, t.sub, t.label, t.scenesLabel]) expect(s).not.toMatch(/\{\w+\}/);
    expect(v.things.map((t) => t.numeral)).toEqual([demoThings(match).against.n, 7, 8]);
  });
});

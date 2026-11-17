import { describe, expect, it } from "vitest";
import data from "../../public/demo/match.json";
import de from "@/messages/de";
import { COURT } from "@handball/court";
import { sampleAt, smooth } from "@/components/anlauf/geometry";
import { ballAt } from "@/components/anlauf/ball";
import { demoFigures, demoGoals, demoScene, goalDistance, halfSpot, reportGoals, SHOT_MIN, zoneOf, type DemoMatch } from "./demo";
import { threeThings } from "./three-things";
import { demoView } from "./things";

const match = data as unknown as DemoMatch;

/** Distance of a court spot (metres, goal at x = 0) to that goal. */
const courtGoalDistance = (x: number, y: number) => goalDistance([y, x]);

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

  it("computes the three things from the data with the app's rule, not by hand", () => {
    const t = threeThings(demoGoals(match));
    expect(t.map((x) => x.key)).toEqual(["conceded_zone", "conceded_fast_breaks", "scored_zone"]);
    expect(t[0]!.of).toBe(match.stats.opponent.goals);
    expect(["m7", "gs"]).not.toContain(t[0]!.zone);
    expect(t[1]!.value).toBe(match.stats.opponent.fast_break_goals);
    expect(match.events.some((e) => e.type === "turnover")).toBe(false);
  });

  it("tells the start page's story: lost 27:29, 11 of 29 conceded over the right wing", () => {
    expect(match.stats.timeline.final).toEqual({ own: 27, opp: 29 });
    const t = threeThings(demoGoals(match));
    expect(t.map((x) => [x.key, x.value, x.of, x.zone])).toEqual([
      ["conceded_zone", 11, 29, "ra"],
      ["conceded_fast_breaks", 5, 29, "gs"],
      ["scored_zone", 9, 27, "kr"],
    ]);
    // the scene on the tactics camera is one of the nine
    expect(demoView(de).sceneGoal.zone).toBe("ra");
    expect(demoGoals(match).every((g) => g.confirmed)).toBe(true);
  });

  it("shows the ball in every frame of the scene: the demo is invented, so we know where it is", () => {
    const v = demoView(de);
    expect(v.scene.ball.length).toBeGreaterThanOrEqual(2);
    expect(v.scene.ball.at(-1)).toMatchObject({ team: "opp", number: v.scene.scorer!.number, to: v.scene.duration });
    for (let i = 0; i <= 300; i++) expect(ballAt(v.scene, i / 300), `t=${i / 300}`).not.toBeNull();
  });

  it("keeps every field player out of both goal areas; only the goalkeeper stands in his", () => {
    const v = demoView(de);
    const scenes = [v.scene, ...demoGoals(match).filter((g) => g.zone !== "gs" && g.zone !== "m7").map((g) => demoScene(g, "x"))];
    for (const scene of scenes) {
      for (const tr of scene.tracks) {
        if (tr.team === "ref") continue;
        for (let i = 0; i <= 200; i++) {
          // court metres, our goal at x = 0, theirs at x = 40
          const [x, y] = sampleAt(tr.xy, i / 200);
          const d = Math.min(courtGoalDistance(x, y), courtGoalDistance(40 - x, y));
          if (tr.keeper) expect(d, "goalkeeper in his area").toBeLessThan(COURT.goalAreaRadius);
          else expect(d, `${tr.team} ${tr.number ?? "?"} at t=${i / 200}`).toBeGreaterThanOrEqual(COURT.goalAreaRadius);
        }
      }
      expect(scene.tracks.filter((x) => x.keeper)).toHaveLength(1);
    }
  });

  it("puts the attack around 9 m and the defence just in front of 6 m", () => {
    const scene = demoView(de).scene;
    const start = (team: "own" | "opp") => scene.tracks.filter((x) => x.team === team && !x.keeper).map((x) => courtGoalDistance(x.xy[0]![0], x.xy[0]![1]));
    const defence = start("own");
    expect(defence).toHaveLength(6);
    for (const d of defence) {
      expect(d).toBeGreaterThanOrEqual(6.4);
      expect(d).toBeLessThan(8);
    }
    const attack = start("opp").sort((a, b) => b - a);
    expect(attack).toHaveLength(6);
    // three backs at 9 m or more, the wings and the pivot closer, all outside 6 m
    expect(attack.slice(0, 3).every((d) => d >= 8.5)).toBe(true);
    expect(attack.every((d) => d >= 6.4)).toBe(true);
  });

  it("starts no run and takes no shot inside the goal area", () => {
    for (const g of demoGoals(match)) {
      for (const p of [...g.run, g.shot]) expect(goalDistance(p), `${g.id} ${g.zone}`).toBeGreaterThanOrEqual(SHOT_MIN - 1e-9);
      for (const p of smooth(g.run, 8)) expect(goalDistance(p), `${g.id} smoothed`).toBeGreaterThanOrEqual(COURT.goalAreaRadius);
    }
  });

  it("gives every figure a source and the match's own numbers", () => {
    const f = demoFigures(match);
    expect(f.find((x) => x.key === "goals")).toMatchObject({ own: match.stats.own.goals, opp: match.stats.opponent.goals, source: "report" });
    expect(f.map((x) => x.key)).not.toContain("turnovers");
    expect(f.find((x) => x.key === "saves")?.source).toBe("marked");
  });

  it("fills in the texts without leftover placeholders", () => {
    const v = demoView(de);
    for (const t of v.things) for (const s of [t.index, t.unit, t.text, t.sub, t.label, t.scenesLabel]) expect(s).not.toMatch(/\{\w+\}/);
    expect(v.things.map((t) => t.numeral)).toEqual(threeThings(demoGoals(match)).map((t) => t.value));
  });
});

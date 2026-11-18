import { describe, expect, it } from "vitest";
import { ballAt } from "@/components/anlauf/ball";
import { demoGoals, demoScene, sceneGap, type DemoGoal } from "./demo";
import { MATCH } from "./things";
import { threeThings } from "./three-things";

/** The ball's way through a scene, in court metres, every tenth of the scene. */
const ballPath = (goal: DemoGoal) => {
  const scene = demoScene(goal, "x");
  return Array.from({ length: 11 }, (_, i) => ballAt(scene, i / 10)!.map((v) => v.toFixed(1)).join(",")).join(" ");
};

describe("every scene on the tactics camera is its own play (U40)", () => {
  const things = threeThings(demoGoals(MATCH));

  it("no two scenes of one thing share the same ball path, and each scene stays the same on every visit", () => {
    for (const thing of things) {
      const goals = thing.goals as DemoGoal[];
      const paths = goals.map(ballPath);
      expect(new Set(paths).size, thing.key).toBe(goals.length);
      expect(goals.map(ballPath)).toEqual(paths);
    }
  });

  it("builds up with two to four passes in a set attack, and varies the build-up", () => {
    for (const thing of [things[0]!, things[2]!]) {
      const goals = thing.goals as DemoGoal[];
      const counts = goals.map((g) => demoScene(g, "x").ball.length - 1);
      for (const n of counts) {
        expect(n).toBeGreaterThanOrEqual(1);
        expect(n).toBeLessThanOrEqual(4);
      }
      expect(new Set(counts).size, thing.key).toBeGreaterThan(1);
      const starters = new Set(goals.map((g) => demoScene(g, "x").ball[0]!.number));
      expect(starters.size, thing.key).toBeGreaterThan(1);
    }
  });

  it("keeps the first thing's message: the right wing catches free in the yellow zone after the defence moved in", () => {
    const goals = things[0]!.goals as DemoGoal[];
    const spots = new Set<string>();
    for (const g of goals) {
      const scene = demoScene(g, "x");
      const gap = sceneGap(scene)!;
      // the ring follows the catch: on the right wing, inside the yellow zone (half court, goal at the top)
      expect(gap.at[0], g.id).toBeGreaterThan(15.4);
      expect(gap.at[1], g.id).toBeLessThan(6.2);
      // free: the nearest defender at least two metres away when the ball arrives
      expect(Math.hypot(gap.near![0] - gap.at[0], gap.near![1] - gap.at[1]), g.id).toBeGreaterThan(2);
      spots.add(gap.at.map((v) => v.toFixed(1)).join(","));
      // the defender on that wing (number 3) has moved in, towards the middle, when the ball arrives
      const wing = scene.tracks.find((x) => x.team === "own" && x.number === 3)!;
      const received = scene.ball.at(-1)!.from / scene.duration;
      const sample = (t: number) => wing.xy[Math.round(t * (wing.xy.length - 1))]!;
      expect(sample(received)[1], g.id).toBeLessThan(gap.at[0] - 1.5);
    }
    expect(spots.size).toBe(goals.length);
  });

  it("varies the fast breaks too: in some the team-mate throws the long pass", () => {
    const goals = things[1]!.goals as DemoGoal[];
    const passes = goals.map((g) => demoScene(g, "x").ball.length);
    expect(passes).toContain(1);
    expect(passes).toContain(2);
  });
});

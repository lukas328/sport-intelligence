import { describe, expect, it } from "vitest";
import type { GoalRun } from "@/components/anlauf/bundle";
import { demoGoals } from "@/lib/demo";
import { MATCH, demoView } from "@/lib/things";
import de from "@/messages/de";
import { MIN_GOALS, MIN_SHARE, threeThings } from "./three-things";
// the app's own rule: the site's copy must give the same result
import * as app from "../../../web/src/lib/three-things";

const g = (team: "own" | "opp", zone: string, i: number): GoalRun => ({ team, zone, run: [], shot: [10, 8], confirmed: true, minute: i });

const CASES: GoalRun[][] = [
  [],
  [g("opp", "rr", 1), g("opp", "rr", 2)],
  [g("opp", "rr", 1), g("opp", "rr", 2), g("opp", "rr", 3), g("opp", "la", 4), g("opp", "gs", 5), g("opp", "gs", 6), g("opp", "gs", 7)],
  [...Array.from({ length: 12 }, (_, i) => g("opp", ["rl", "rm", "rr", "kr"][i % 4]!, i)), ...Array.from({ length: 9 }, (_, i) => g("own", i < 4 ? "kr" : "m7", i))],
];

describe("three things", () => {
  it("uses the app's thresholds", () => {
    expect(MIN_GOALS).toBe(app.MIN_GOALS);
    expect(MIN_SHARE).toBe(app.MIN_SHARE);
  });

  it.each(CASES.map((c, i) => [i, c] as const))("case %i gives the same as the app", (_, goals) => {
    expect(threeThings(goals)).toEqual(app.threeThings(goals));
  });

  it("gives the demo match the same three things as the app would", () => {
    const goals = demoGoals(MATCH);
    const ours = threeThings(goals).map((t) => [t.key, t.value, t.of, t.zone]);
    expect(ours).toEqual(app.threeThings(goals).map((t) => [t.key, t.value, t.of, t.zone]));
    expect(ours.map((t) => t[0])).toEqual(["conceded_zone", "conceded_fast_breaks", "scored_zone"]);
    expect(demoView(de).things.map((t) => t.numeral)).toEqual(ours.map((t) => t[1]));
  });
});

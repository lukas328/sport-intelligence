import { describe, expect, it } from "vitest";
import type { GoalRun } from "@/components/anlauf/bundle";
import { threeThings } from "./three-things";

const goal = (team: "own" | "opp", zone: string): GoalRun => ({ team, zone, run: [], shot: [10, 5], confirmed: true });
const many = (n: number, team: "own" | "opp", zone: string) => Array.from({ length: n }, () => goal(team, zone));

describe("three things", () => {
  it("says the opponent's main zone, its fast breaks and our main zone, with their base", () => {
    const goals = [...many(9, "opp", "ra"), ...many(6, "opp", "gs"), ...many(3, "opp", "rl"), ...many(7, "own", "kr"), ...many(19, "own", "rm"), ...many(2, "own", "m7")];
    const things = threeThings(goals);
    expect(things.map((t) => [t.key, t.value, t.of, t.zone])).toEqual([
      ["conceded_zone", 9, 18, "ra"],
      ["conceded_fast_breaks", 6, 18, "gs"],
      ["scored_zone", 19, 28, "rm"],
    ]);
    expect(things[0]!.rest).toHaveLength(9);
  });

  it("says nothing without enough goals", () => {
    expect(threeThings([...many(2, "opp", "ra"), ...many(2, "own", "kr")])).toEqual([]);
    // a zone with a small share is no statement
    expect(threeThings([...many(3, "opp", "ra"), ...many(4, "opp", "la"), ...many(4, "opp", "rl"), ...many(4, "opp", "rr")]).map((t) => t.zone)).toEqual(["la"]);
  });
});

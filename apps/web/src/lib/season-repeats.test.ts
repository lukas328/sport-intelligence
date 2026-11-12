import { describe, expect, it } from "vitest";
import type { GoalRun } from "@/components/anlauf/bundle";
import { seasonRepeats, shortName, type SeasonMatch } from "./season-repeats";

const g = (team: "own" | "opp", zone: string): GoalRun => ({ team, zone, run: [], shot: [0, 0], aim: null, confirmed: true });
const many = (n: number, team: "own" | "opp", zone: string) => Array.from({ length: n }, () => g(team, zone));
const m = (id: string, goals: GoalRun[], turnovers = 10): SeasonMatch => ({ id, label: id, goals, turnovers });

describe("seasonRepeats", () => {
  it("finds the conceded zone of the season with one bar per match", () => {
    const r = seasonRepeats([m("a", [...many(5, "opp", "ra"), ...many(2, "opp", "rl")]), m("b", [...many(5, "opp", "ra"), ...many(4, "opp", "kr")]), m("c", [...many(9, "opp", "ra"), ...many(3, "opp", "gs")])]);
    expect(r.conceded?.zone).toBe("ra");
    expect(r.conceded?.series).toEqual([5, 5, 9]);
    expect(r.conceded?.value).toBe(19);
    expect(r.conceded?.of).toBe(28);
    expect(r.conceded?.everyMatch).toBe(true);
  });
  it("leaves fast breaks and 7 m out of the conceded zone", () => {
    const r = seasonRepeats([m("a", many(6, "opp", "gs")), m("b", many(6, "opp", "m7"))]);
    expect(r.conceded).toBeNull();
  });
  it("says nothing with one match or too few goals", () => {
    expect(seasonRepeats([m("a", many(9, "opp", "ra"))]).conceded).toBeNull();
    expect(seasonRepeats([m("a", many(1, "own", "kr")), m("b", many(1, "own", "kr"))]).scored).toBeNull();
  });
  it("marks a rising series", () => {
    const r = seasonRepeats([m("a", many(3, "own", "kr")), m("b", many(4, "own", "kr")), m("c", many(7, "own", "kr"))]);
    expect(r.scored?.rising).toBe(true);
  });
  it("names one turnover outlier", () => {
    expect(seasonRepeats([m("a", [], 10), m("b", [], 15), m("c", [], 11)]).turnovers).toMatchObject({ median: 11, outlier: 1 });
    expect(seasonRepeats([m("a", [], 10), m("b", [], 12), m("c", [], 11)]).turnovers?.outlier).toBeNull();
  });
  it("shortens opponent names", () => {
    expect(shortName("BSV Stäfa-Uerikon")).toBe("Stäfa");
    expect(shortName("TSV Thalwil-Gattikon")).toBe("Thalwil");
    expect(shortName("TV Rüti")).toBe("Rüti");
    expect(shortName("TV Au-Wädenswil")).toBe("Wädenswil");
  });
});

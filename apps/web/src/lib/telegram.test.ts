import { describe, expect, it } from "vitest";
import { halfScore, mainKeeper, mainSource, scoreSequence, shortName, topScorers } from "./telegram";

const pts = [
  { clock_s: 0, own: 0, opp: 0 },
  { clock_s: 100, own: 1, opp: 0 },
  { clock_s: 500, own: 1, opp: 1 },
  { clock_s: 1700, own: 2, opp: 1 },
  { clock_s: 2000, own: 2, opp: 2 },
  { clock_s: 3500, own: 3, opp: 2 },
];

describe("telegram", () => {
  it("gives the half-time score only with times", () => {
    expect(halfScore(pts, 1800)).toEqual([2, 1]);
    expect(halfScore(pts, 1800, false)).toBeNull();
    expect(halfScore([pts[0]!], 1800)).toBeNull();
  });

  it("samples the score every five minutes, each change once, the final last", () => {
    expect(scoreSequence(pts, 1800)).toEqual([[1, 0], [1, 1], [2, 1], [2, 2], [3, 2]]);
    expect(scoreSequence(pts, 1800, 2, false)).toEqual([]);
  });

  it("names scorers and the keeper by surname", () => {
    expect(shortName("Lea Brunner", 7)).toBe("Brunner");
    expect(shortName(undefined, 7)).toBe("#7");
    const players = [
      { side: "own" as const, player_id: "a", number: 7, goals: 7, seven_m_goals: 0 },
      { side: "own" as const, player_id: "b", number: 9, goals: 5, seven_m_goals: 2 },
      { side: "opponent" as const, player_id: null, number: 3, goals: 9, seven_m_goals: 0 },
    ];
    expect(topScorers(players, { a: "Lea Brunner", b: "Mia Graf" })).toEqual(["Brunner 7", "Graf 5/2"]);
    expect(topScorers(players, { a: "Lea Brunner", b: "Mia Graf" }, 3, (k) => ` (${k} vom 7-m)`)).toEqual(["Brunner 7", "Graf 5 (2 vom 7-m)"]);
    expect(mainKeeper([{ side: "own", player_id: "k", number: 1, saves: 11 }], { k: "Nora Meier" })).toEqual({ name: "Meier", saves: 11 });
    expect(mainKeeper([{ side: "own", player_id: "k", number: 1, saves: 0 }], {})).toBeNull();
  });

  it("says where the figures come from", () => {
    expect(mainSource({ paper_report: 40, model: 3 })).toBe("report");
    expect(mainSource({ user_correction: 40 })).toBe("marked");
    expect(mainSource({ model: 4 })).toBe("video");
  });
});

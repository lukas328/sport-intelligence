import { describe, expect, it } from "vitest";
import { signed, tableExcerpt, type TableRow } from "./league-table";

const table = (n: number, own?: number, marked?: number): TableRow[] =>
  Array.from({ length: n }, (_, i) => ({ key: String(i), rank: i + 1, name: `Team ${i + 1}`, games: 10, diff: 0, points: 20 - i, own: i === own, marked: i === marked }));

describe("league table", () => {
  it("shows five rows around the own team", () => {
    expect(tableExcerpt(table(12, 6)).map((r) => r.rank)).toEqual([5, 6, 7, 8, 9]);
    expect(tableExcerpt(table(12, 0)).map((r) => r.rank)).toEqual([1, 2, 3, 4, 5]);
    expect(tableExcerpt(table(12, 11)).map((r) => r.rank)).toEqual([8, 9, 10, 11, 12]);
  });

  it("shows a short table whole and the top without the own team", () => {
    expect(tableExcerpt(table(6, 2))).toHaveLength(6);
    expect(tableExcerpt(table(12)).map((r) => r.rank)).toEqual([1, 2, 3, 4, 5]);
  });

  it("shows the own team and the next opponent with their neighbours", () => {
    expect(tableExcerpt(table(12, 1, 9)).map((r) => r.rank)).toEqual([1, 2, 3, 9, 10, 11]);
  });

  it("writes the goal difference with its sign", () => {
    expect([signed(3), signed(-2), signed(0), signed(null)]).toEqual(["+3", "-2", "0", ""]);
  });
});

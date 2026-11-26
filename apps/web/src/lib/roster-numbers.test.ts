import { describe, expect, it } from "vitest";
import { numberGaps, parseQuickRoster, quickCsv } from "./roster-numbers";

// invented players
const p = (n: number | null, first: string, last: string) => ({ jersey_number: n, first_name: first, last_name: last });

describe("numberGaps: who has no number, which number two share", () => {
  it("finds both, lowest number first", () => {
    const g = numberGaps([p(7, "Lena", "Muster"), p(null, "Mia", "Beispiel"), p(12, "Noa", "Probst"), p(7, "Ella", "Test"), p(3, "Ida", "Ruf"), p(3, "Zoe", "Wald")]);
    expect(g.without.map((e) => e.first_name)).toEqual(["Mia"]);
    expect(g.duplicates.map(([n, l]) => [n, l.map((e) => e.first_name)])).toEqual([
      [3, ["Ida", "Zoe"]],
      [7, ["Lena", "Ella"]],
    ]);
  });
  it("nothing for a complete squad", () => {
    expect(numberGaps([p(1, "A", "B"), p(2, "C", "D")])).toEqual({ without: [], duplicates: [] });
  });
});

describe("parseQuickRoster: number and name per line", () => {
  it("reads the usual ways to write a squad", () => {
    const rows = parseQuickRoster("7 Lena Muster\n#10 Mia Beispiel\n12. Noa von Probst\nIda Ruf 3\n 9 - Zoe Wald \n\nElla Test");
    expect(rows.map((r) => [r.number, r.first, r.last, r.error])).toEqual([
      [7, "Lena", "Muster", null],
      [10, "Mia", "Beispiel", null],
      [12, "Noa", "von Probst", null],
      [3, "Ida", "Ruf", null],
      [9, "Zoe", "Wald", null],
      [null, "Ella", "Test", null], // no number: kept, the coach is told
    ]);
    expect(rows.map((r) => r.line)).toEqual([1, 2, 3, 4, 5, 7]);
  });

  it("reads columns pasted from a spreadsheet", () => {
    expect(parseQuickRoster("7\tLena\tMuster\n8;Mia;Beispiel").map((r) => [r.number, r.first, r.last])).toEqual([
      [7, "Lena", "Muster"],
      [8, "Mia", "Beispiel"],
    ]);
  });

  it("marks a missing name, a number out of range and a number given twice", () => {
    const rows = parseQuickRoster("7 Lena\n100 Mia Beispiel\n0 Ida Ruf\n7 Lena Muster\n7 Noa Probst");
    expect(rows.map((r) => r.error)).toEqual(["name", "number", "number", null, "twice"]);
  });
});

describe("quickCsv: the good rows for the squad import", () => {
  it("writes Nr;Vorname;Nachname, quoted, without the faulty rows", () => {
    expect(quickCsv(parseQuickRoster('7 Lena Muster\n8 Mia\nElla "Elli" Test'))).toBe('Nr;Vorname;Nachname\n7;"Lena";"Muster"\n;"Ella";"""Elli"" Test"');
  });
});

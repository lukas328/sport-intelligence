import { describe, expect, it } from "vitest";
import { duplicateNumbers, groupSuggestions, parseNumber, sevenM, standingByRank, type Suggestion } from "./official-suggestions";

const s = (id: string, kind: Suggestion["kind"], payload: Record<string, unknown>, status: Suggestion["status"] = "open"): Suggestion => ({
  id,
  kind,
  status,
  payload,
  created_at: "2026-11-09T08:00:00Z",
  resolved_at: null,
});

describe("official suggestions", () => {
  it("group the squad by kind and appearances, reports by date", () => {
    const g = groupSuggestions([
      s("a", "roster_add", { last_name: "Zeller", appearances: 1 }),
      s("b", "roster_left", { last_name: "Aebi" }),
      s("c", "roster_add", { last_name: "Meier", appearances: 6 }),
      s("d", "report", { kickoff_at: "2026-10-12T14:00:00+02:00" }),
      s("e", "report", { kickoff_at: "2026-10-04T14:00:00+02:00" }),
      s("f", "roster_add", { last_name: "Huber", appearances: 6 }, "accepted"),
      s("g", "match_moved", { kickoff_at: "2026-11-20T19:00:00+01:00" }),
    ]);
    expect(g.roster.map((x) => x.id)).toEqual(["c", "a", "b"]);
    expect(g.reports.map((x) => x.id)).toEqual(["e", "d"]);
    expect(g.schedule.map((x) => x.id)).toEqual(["g"]);
  });
  it("read shirt numbers and 7 m", () => {
    expect(parseNumber("")).toBeNull();
    expect(parseNumber(" 7 ")).toBe(7);
    expect(parseNumber("100")).toBeUndefined();
    expect(sevenM(null)).toBe("-");
    expect(sevenM({ goals_7m: 3, attempts_7m: 5 } as never)).toBe("3/5");
  });
  it("find numbers given twice", () => {
    expect([...duplicateNumbers([22, 5, null, 22, undefined, 7])]).toEqual([22]);
  });
});

describe("standingByRank", () => {
  it("orders the table by rank and keeps rows without one at the end", () => {
    const rows = [{ rank: 2, name: "B" }, { name: "X" }, { rank: 1, name: "A" }];
    expect(standingByRank(rows).map((r) => r.name)).toEqual(["A", "B", "X"]);
  });
});

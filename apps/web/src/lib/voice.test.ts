import { describe, expect, it } from "vitest";
import { focusMetric, matchStatement, seasonStatement, xgGap, type SeasonRow } from "./voice";

const row = (own: number, opp: number, xg = own, xga = opp, day = 1): SeasonRow => ({
  score_own: own,
  score_opponent: opp,
  xg,
  xg_against: xga,
  kickoff_at: `2026-10-${String(day).padStart(2, "0")}T18:00:00Z`,
});

describe("voice", () => {
  it("only calls a clear gap between goals and xG", () => {
    expect(xgGap(22, 14.3)).toBe("over");
    expect(xgGap(20, 21)).toBeNull();
    expect(xgGap(15, 21)).toBe("under");
    expect(xgGap(3, 0)).toBeNull();
    // an estimate off by more than double is not a statement about the team
    expect(xgGap(26, 3.4)).toBeNull();
    expect(xgGap(5, 20)).toBeNull();
  });

  it("says nothing without data", () => {
    expect(seasonStatement([])).toBeNull();
    expect(matchStatement({ own: null, opp: null, opponent: "X" })).toBeNull();
  });

  it("states a run first, then the attack against xG, then the defence", () => {
    const run = seasonStatement([row(20, 18, 20, 18, 1), row(25, 20, 25, 20, 2), row(30, 21, 30, 21, 3)]);
    expect(run?.headline).toEqual({ key: "voice.runWins", params: { n: 3 } });
    expect(run?.evidence).toEqual({ key: "voice.record", params: { w: 3, d: 0, l: 0 } });
    const over = seasonStatement([row(22, 20, 14.3, 20)]);
    expect(over?.headline.key).toBe("voice.overXg");
    expect(over?.evidence).toEqual({ key: "voice.xgEvidence", params: { goals: 22, xg: 14.3 } });
    // too few shots with a position: the xG sum says nothing
    expect(seasonStatement([row(22, 20, 14.3, 20)], 0.3)?.headline.key).not.toBe("voice.overXg");
    expect(seasonStatement([row(22, 20, 14.3, 20)], 0.9)?.headline.key).toBe("voice.overXg");
    const held = seasonStatement([row(22, 15, 22, 21)]);
    expect(held?.headline.key).toBe("voice.defenceHeld");
    // nothing stands out in a single match: neutral title
    expect(seasonStatement([row(22, 20)])).toBeNull();
    expect(seasonStatement([row(22, 20, 22, 20, 1), row(18, 24, 18, 24, 2)])?.headline.key).toBe("voice.level");
  });

  it("describes a match by its margin and marks xG as estimated in the evidence", () => {
    expect(matchStatement({ own: 22, opp: 20, opponent: "TV" })?.headline).toEqual({ key: "voice.won", params: { opponent: "TV" } });
    expect(matchStatement({ own: 21, opp: 20, opponent: "TV" })?.headline.key).toBe("voice.wonTight");
    expect(matchStatement({ own: 30, opp: 20, opponent: "TV" })?.headline.key).toBe("voice.wonClear");
    expect(matchStatement({ own: 20, opp: 20, opponent: "TV" })?.headline.key).toBe("voice.draw");
    expect(matchStatement({ own: 19, opp: 20, opponent: "TV" })?.headline.key).toBe("voice.lostTight");
    expect(matchStatement({ own: 22, opp: 20, opponent: "TV", xg: 14.3 })?.evidence?.key).toBe("voice.matchOverXg");
  });

  it("marks one figure to work on, only when clearly below the reference", () => {
    expect(focusMetric({ save_pct: 0.23, shooting_pct: 0.71, turnovers_per_match: 4 })).toBe("save_pct");
    expect(focusMetric({ save_pct: 0.33, shooting_pct: 0.6, turnovers_per_match: 10 })).toBeNull();
    expect(focusMetric({ save_pct: null, shooting_pct: 0.4, turnovers_per_match: 15 })).toBe("shooting_pct");
  });
});

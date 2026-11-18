import { describe, expect, it } from "vitest";
import { goalsBy, MATCH_SECONDS, matchClock, scoreAt, scorerOf, videoPan } from "./match-run";
import { matchPhases } from "./week";

describe("Saturday in 20 seconds: video and line on one clock (U36)", () => {
  const { score, phases } = matchPhases();

  it("ends on the final score at 60:00, the end state without JavaScript and with reduced motion", () => {
    expect(scoreAt(score, MATCH_SECONDS)).toMatchObject({ own: 27, opp: 29 });
    expect(matchClock(MATCH_SECONDS)).toBe("60:00");
    expect(matchClock(MATCH_SECONDS + 30)).toBe("60:00");
    expect(matchClock(0)).toBe("0:00");
    expect(matchClock(15 * 60 + 28.7)).toBe("15:28");
    expect(goalsBy(score, MATCH_SECONDS)).toBe(56);
  });

  it("counts a goal exactly when the line makes its step, and knows who scored", () => {
    const goals = score.slice(1);
    for (const [i, g] of goals.entries()) {
      expect(goalsBy(score, g.clock_s - 0.01)).toBe(i);
      expect(goalsBy(score, g.clock_s)).toBe(i + 1);
      const before = score[i]!;
      expect(scorerOf(score, i + 1)).toBe(g.own > before.own ? "own" : "opp");
    }
    expect(scorerOf(score, 0)).toBeNull();
    // the turn: four goals for the opponent in a row
    const run = phases[1]!;
    const inTurn = goals.filter((g) => g.clock_s > run.from && g.clock_s <= run.to);
    expect(inTurn).toHaveLength(4);
    expect(inTurn.map((g) => scorerOf(score, goals.indexOf(g) + 1))).toEqual(["opp", "opp", "opp", "opp"]);
  });

  it("moves the camera while the match runs and rests centred at the end", () => {
    expect(videoPan(MATCH_SECONDS)).toEqual({ scale: 1.08, x: 0, y: 0 });
    expect(videoPan(0)).toEqual({ scale: 1.12, x: 0, y: 0 });
    const mid = videoPan(MATCH_SECONDS / 28);
    expect(Math.abs(mid.x)).toBeGreaterThan(3);
    // never pans past the picture's edge: the zoom leaves (scale - 1) / 2 on each side
    for (let s = 0; s <= MATCH_SECONDS; s += 15) {
      const p = videoPan(s);
      expect(Math.abs(p.x) * p.scale).toBeLessThan(((p.scale - 1) / 2) * 100);
    }
  });
});

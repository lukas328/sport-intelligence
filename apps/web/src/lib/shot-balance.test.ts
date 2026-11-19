import { describe, expect, it } from "vitest";
import { courseOf } from "./score-flow";
import { MIN_COVERED_S, teamCovered } from "./physical-cover";
import { shotBalance, withoutPosition } from "./shot-balance";

const known = { shooting: true, saving: true, turnovers: false };

describe("one account of the shots (app review BUG-08)", () => {
  // the observed match of the review: 9 shots, 6 goals, 2 saved by the other keeper, 1 miss;
  // the other side only 1 goal
  const own = { goals: 6, shots: 9, shots_blocked: 0, misses: 1, posts: 0, saves: 0, known };
  const opp = { goals: 1, shots: 1, shots_blocked: 0, misses: 0, posts: 0, saves: 2, known: { ...known, shooting: false } };

  it("adds up: goals + saved + misses + posts = shots on target", () => {
    const b = shotBalance(own, opp);
    expect(b.known).toBe(true);
    expect(b.goals + b.saved + b.misses + b.posts + b.other).toBe(b.shots);
    expect(b.other).toBe(0);
    expect(b.saved).toBe(2);
  });

  it("says «only goals» for a side without recorded attempts, no figure mixed in", () => {
    expect(shotBalance(opp, own).known).toBe(false);
  });

  it("names shots the outcomes do not explain instead of hiding them", () => {
    expect(shotBalance({ ...own, shots: 11 }, opp).other).toBe(2);
  });

  it("counts shots without a position as shots less placed shots", () => {
    expect(withoutPosition(9, 1)).toBe(8);
    expect(withoutPosition(0, 0)).toBe(0);
  });
});

describe("the course of the match over what the data covers (BUG-20)", () => {
  it("runs over the video's own minutes without a throw-off", () => {
    expect(courseOf({ has_report: false, span: null }, null, 480)).toEqual({ span: [0, 8], video: true });
  });
  it("takes the match minutes of the video when known", () => {
    expect(courseOf({ has_report: false, span: [12, 20] }, { "1": 1000 }, 480)).toEqual({ span: [12, 20], video: false });
  });
  it("spans the whole match with a report", () => {
    expect(courseOf({ has_report: true, span: [12, 20] }, null, 480)).toBeNull();
  });
});

describe("running figures cover the video, not the longest track (BUG-11)", () => {
  const home = (team: string | null | undefined) => team === "home";
  it("counts from the first to the last moment of the team's tracks", () => {
    const data = {
      players: [],
      tracks: [
        { team: "home", first_ms: 0, last_ms: 50_000 },
        { team: "home", first_ms: 200_000, last_ms: 480_000 },
        { team: "away", first_ms: 0, last_ms: 900_000 },
      ],
    };
    expect(teamCovered(data, home)).toBe(480);
  });
  it("leaves a team out below two minutes of video", () => {
    const data = { players: [], tracks: [{ team: "home", first_ms: 0, last_ms: 60_000 }] };
    expect(teamCovered(data, home)).toBeLessThan(MIN_COVERED_S);
  });
});

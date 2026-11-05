import { describe, expect, it } from "vitest";
import { clockAt, coverage, covered, firstOpen, inside, kickoffMissing, steps, type StepInput } from "./match-workflow";

const HALF = 1800;

describe("coverage", () => {
  it("is unknown without a throw-off", () => {
    expect(coverage({}, HALF, 300_000)).toBeNull();
    expect(coverage(null, HALF, 300_000)).toBeNull();
  });

  it("places a short clip of the first half on the match clock", () => {
    // a 5 minute clip whose throw-off is at 0:20 in the video
    const spans = coverage({ "1": 20_000 }, HALF, 300_000)!;
    expect(spans).toEqual([{ from: 0, to: 280 }]);
    expect(covered(spans)).toBe(280);
    expect(inside(100, spans)).toBe(true);
    expect(inside(900, spans)).toBe(false);
  });

  it("starts a clip from the middle of a half where it starts", () => {
    // 5 minutes from 12:40 of the first half: the throw-off lies 760 s before the video
    expect(coverage({ "1": -760_000 }, HALF, 300_000)).toEqual([{ from: 760, to: 1060 }]);
  });

  it("covers both halves of a full game and stops the first at the second throw-off", () => {
    const spans = coverage({ "1": 60_000, "2": 60_000 + 1800_000 + 600_000 }, HALF, 4_500_000)!;
    expect(spans[0]).toEqual({ from: 0, to: HALF });
    expect(spans[1]!.from).toBe(HALF);
    expect(spans[1]!.to).toBe(HALF + HALF);
  });

  it("ends the first half at the second throw-off when that comes early", () => {
    const spans = coverage({ "1": 0, "2": 1000_000 }, HALF, 1_200_000)!;
    expect(spans[0]).toEqual({ from: 0, to: 1000 });
    expect(spans[1]).toEqual({ from: HALF, to: HALF + 200 });
  });
});

describe("kickoffMissing", () => {
  it("asks for the first half first", () => expect(kickoffMissing({}, HALF, 300_000)).toEqual([1]));
  it("needs no second half for a clip of the first", () => expect(kickoffMissing({ "1": 0 }, HALF, 300_000)).toEqual([]));
  it("asks for the second half when the video runs past halftime", () =>
    expect(kickoffMissing({ "1": 0 }, HALF, 4_000_000)).toEqual([2]));
  it("is done with both", () => expect(kickoffMissing({ "1": 0, "2": 2_400_000 }, HALF, 4_000_000)).toEqual([]));
});

const base: StepInput = {
  analysis: { status: "ready", needsCalibration: false, unconfirmed: false },
  kickoff: { "1": 0 },
  periodS: HALF,
  durationMs: 300_000,
  candidatesOpen: 0,
  officialOpen: 0,
  unassigned: 0,
};

describe("steps", () => {
  it("is all done for a checked clip", () => {
    expect(steps(base).map((s) => s.state)).toEqual(["done", "done", "done", "done"]);
    expect(firstOpen(steps(base))).toBeNull();
  });

  it("puts the court first while it needs four clicks", () => {
    const s = steps({ ...base, analysis: { status: "ready", needsCalibration: true, unconfirmed: false }, candidatesOpen: 4 });
    expect(s[0]).toEqual({ id: "court", state: "open", reason: "mark" });
    expect(firstOpen(s)).toBe("court");
  });

  it("asks to check an automatic court that nobody confirmed", () =>
    expect(steps({ ...base, analysis: { status: "ready", needsCalibration: false, unconfirmed: true } })[0]!.reason).toBe("check"));

  it("waits while the analysis runs", () =>
    expect(steps({ ...base, analysis: { status: "running", needsCalibration: false, unconfirmed: false } })[0]!.state).toBe("waiting"));

  it("adds open candidates and open official goals", () => {
    const goals = steps({ ...base, candidatesOpen: 12, officialOpen: 2 })[2]!;
    expect(goals).toEqual({ id: "goals", state: "open", count: 14 });
  });

  it("waits for goals when there is neither list", () =>
    expect(steps({ ...base, candidatesOpen: null, officialOpen: null })[2]!.state).toBe("waiting"));

  it("counts tracks without a player", () => {
    const s = steps({ ...base, kickoff: {}, unassigned: 9 });
    expect(s[1]).toEqual({ id: "kickoff", state: "open", reason: "period1" });
    expect(s[3]).toEqual({ id: "players", state: "open", count: 9 });
    expect(firstOpen(s)).toBe("kickoff");
  });
});

describe("clockAt", () => {
  it("is null before the first throw-off", () => expect(clockAt({ "1": 10_000 }, HALF, 5_000)).toBeNull());
  it("counts from the throw-off of the half", () => {
    expect(clockAt({ "1": 10_000 }, HALF, 70_000)).toBe(60);
    expect(clockAt({ "1": 0, "2": 2_400_000 }, HALF, 2_460_000)).toBe(HALF + 60);
  });
});

describe("throw-off read from a clip", () => {
  it("is done and says so when the video starts later in the half", () =>
    expect(steps({ ...base, kickoff: { "1": -760_000 } })[1]).toEqual({ id: "kickoff", state: "done", reason: "fromClip" }));
});

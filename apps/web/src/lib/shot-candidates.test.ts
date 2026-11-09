import { describe, expect, it } from "vitest";
import type { Candidate, CandidateList } from "./goal-candidates";
import { defaultSide, shotAnswer, shotKeyAction, visibleShots, withShotReview, type ReportShot } from "./shot-candidates";

const report = (over: Partial<ReportShot> = {}): ReportShot => ({
  event_id: "r1",
  side: "opponent",
  outcome: "save",
  penalty: false,
  number: 7,
  player_id: null,
  name: "Muster",
  period: 1,
  clock_s: 780,
  official_time: "13:00",
  t_ms: 40_000,
  uncertainty_ms: 2000,
  ...over,
});

const cand = (id: string, rate: number, over: Partial<Candidate> = {}): Candidate => ({
  id,
  kind: "shot",
  video_asset_id: "v",
  t_ms: 40_000,
  goal_ms: 39_000,
  start_ms: 32_000,
  end_ms: 44_000,
  score: 1,
  rate,
  suggested_side: null,
  status: "open",
  side: null,
  event_id: null,
  period: 1,
  clock_s: 775,
  known: null,
  outcome: null,
  suggestion: null,
  ...over,
});

const list = (candidates: Candidate[]): CandidateList => ({
  kind: "shot",
  template: null,
  rates: [2, 4, 6],
  default_rate: 4,
  counts: { total: candidates.length, open: 0, open_by_rate: {}, confirmed: 0, rejected: 0, known: 0, suggested: 0 },
  candidates,
});

describe("shot candidate keys", () => {
  it("use the tagger's letters for outcomes and 1 / 2 for the team", () => {
    expect(shotKeyAction("G")).toEqual({ kind: "outcome", outcome: "goal" });
    expect(shotKeyAction("b")).toEqual({ kind: "outcome", outcome: "blocked" });
    expect(shotKeyAction("2")).toEqual({ kind: "side", side: "opponent" });
    expect(shotKeyAction("Enter")).toEqual({ kind: "accept" });
    expect(shotKeyAction("q")).toBeNull();
  });
});

describe("shot answers", () => {
  const withReport = cand("a", 2, { suggestion: report(), suggested_side: "own" });
  it("Enter takes the report entry", () => {
    expect(shotAnswer(withReport, null, "accept")).toEqual({ status: "confirmed" });
    expect(shotAnswer(cand("b", 2), null, "accept")).toBeNull();
  });
  it("the report's own answer pins the entry; another one is the coach's shot", () => {
    expect(shotAnswer(withReport, null, "save")).toEqual({ status: "confirmed" });
    expect(shotAnswer(withReport, null, "goal")).toEqual({ status: "confirmed", side: "opponent", outcome: "goal" });
    expect(shotAnswer(withReport, "own", "save")).toEqual({ status: "confirmed", side: "own", outcome: "save" });
  });
  it("needs a team when neither the report nor the analysis has one", () => {
    expect(shotAnswer(cand("c", 2), null, "miss")).toBeNull();
    expect(shotAnswer(cand("c", 2, { suggested_side: "own" }), null, "miss")).toEqual({ status: "confirmed", side: "own", outcome: "miss" });
  });
  it("the report's team comes before the analysis' guess", () => {
    expect(defaultSide(withReport)).toBe("opponent");
  });
});

describe("visible shots", () => {
  const l = list([cand("a", 6, { suggestion: report() }), cand("b", 2), cand("c", 6), cand("d", 6, { status: "rejected" })]);
  it("with a report entry at any rate", () => {
    expect(visibleShots(l, 2, "report").map((c) => c.id)).toEqual(["a"]);
  });
  it("open at the chosen rate; all keeps decided rows", () => {
    expect(visibleShots(l, 2, "open").map((c) => c.id)).toEqual(["b"]);
    expect(visibleShots(l, 2, "all").map((c) => c.id)).toEqual(["b", "d"]);
  });
  it("an answer leaves the open lists and updates the counts", () => {
    const after = withShotReview(l, "a", { status: "confirmed" });
    expect(after.candidates[0]).toMatchObject({ status: "confirmed", side: "opponent", outcome: "save" });
    expect(after.counts).toMatchObject({ confirmed: 1, suggested: 0, open: 2 });
    expect(withShotReview(after, "a", { status: null }).candidates[0]).toMatchObject({ status: "open", outcome: null });
  });
});

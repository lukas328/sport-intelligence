import { describe, expect, it } from "vitest";
import { cameraScene, goalRuns, reportGoals, spotless, videoScore, type MatchGraphics, type SceneCamera } from "./graphics";

const G: MatchGraphics = {
  has_video: true,
  field_confirmed: true,
  report_goals: [
    { minute: 1.5, team: "own" },
    { minute: null, team: "opp" },
  ],
  goals: [
    { event_id: "a", team: "own", minute: 1.5, number: 7, zone: "la", run: [[2, 6], [1.5, 1.5]], shot: [1.5, 1.5], aim: null, confirmed: true, source: "tracking", has_video: true },
    { event_id: "b", team: "opp", minute: 3, number: null, zone: null, run: [], shot: [10, 8], aim: null, confirmed: false, source: "marked", has_video: false },
  ],
  phases: [],
  checks: [],
  source: "analysis",
};

const S: SceneCamera = {
  event_id: "a",
  clock_s: 84,
  duration_s: 6,
  field_confirmed: true,
  tracks: [{ team: "own", number: 7, xy: [[3, 4], [2, 3]] }],
  ball: [],
  scorer: { team: "own", number: 7 },
  shot: [2, 3],
  confirmed: true,
  source: "analysis",
};

describe("graphics data", () => {
  it("keeps the goal sequence with minutes only", () => {
    expect(reportGoals(G)).toEqual([{ minute: 1.5, team: "own" }]);
  });

  it("draws a goal without tracking as its spot, estimated when not confirmed", () => {
    const [own] = goalRuns(G, "own");
    expect(own).toMatchObject({ eventId: "a", run: [[2, 6], [1.5, 1.5]], confirmed: true });
    const [opp] = goalRuns(G, "opp");
    expect(opp).toMatchObject({ run: [], shot: [10, 8], confirmed: false });
  });

  it("shows no camera without a confirmed court or without positions", () => {
    expect(cameraScene(S)).toMatchObject({ clock: 84, duration: 6, ball: [] });
    expect(cameraScene({ ...S, field_confirmed: false })).toBeNull();
    expect(cameraScene({ ...S, tracks: [] })).toBeNull();
  });

  it("keeps a confirmed goal without a spot: counted, listed, not drawn (real-video test E01, E10)", () => {
    const g: MatchGraphics = { ...G, goals: [...G.goals, { event_id: "c", team: "opp", minute: null, number: null, zone: null, run: [], shot: null, aim: null, confirmed: true, source: null, has_video: true, t_ms: 90_000 }] };
    expect(goalRuns(g).map((x) => x.eventId)).toEqual(["a", "b"]);
    expect(spotless(g).map((x) => x.event_id)).toEqual(["c"]);
    // the score counts the goals with a place in the video (b is a report goal without one)
    expect(videoScore(g)).toEqual({ own: 1, opp: 1 });
    expect(videoScore({ ...G, goals: [] })).toBeNull();
  });

  it("shows positions without a match clock, on the video time (real-video test E02)", () => {
    expect(cameraScene({ ...S, clock_s: null, video_s: 312 })).toMatchObject({ clock: 312, videoTime: true });
    expect(cameraScene(S)).toMatchObject({ videoTime: false });
  });
});

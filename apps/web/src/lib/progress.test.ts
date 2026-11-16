import { describe, expect, it } from "vitest";
import { durationParts, headlineKey, isActive, stepState, tone, withLocal, type FileProgress, type MatchProgress } from "./progress";
import { localEta, type LocalUpload } from "./upload-store";

const file = (extra: Partial<FileProgress> = {}): FileProgress => ({
  video_id: "v1",
  filename: "spiel.mp4",
  role: "main",
  stage: "upload",
  state: "running",
  overall: 0.02,
  fraction: 0.2,
  restarted: false,
  ...extra,
});

const match = (files: FileProgress[], extra: Partial<MatchProgress> = {}): MatchProgress => ({
  match_id: "m1",
  team_id: "t1",
  kind: "match",
  opponent_name: "TV Gegner",
  kickoff_at: "2026-11-16T18:00:00Z",
  is_home: true,
  stage: files[0]?.stage ?? "done",
  state: files[0]?.state ?? "done",
  overall: 0.02,
  files,
  ...extra,
});

describe("the progress in words (K6, K13)", () => {
  it("rounds durations the way people say them", () => {
    expect(durationParts(30)).toEqual({ h: 0, m: 1 });
    expect(durationParts(7 * 60 + 10)).toEqual({ h: 0, m: 8 });
    expect(durationParts(23 * 60)).toEqual({ h: 0, m: 25 });
    expect(durationParts(95 * 60)).toEqual({ h: 1, m: 35 });
    expect(durationParts(119.5 * 60)).toEqual({ h: 2, m: 0 });
  });

  it("names what runs, and what needs a look", () => {
    expect(headlineKey(match([file()]))).toBe("headUpload");
    expect(headlineKey(match([file({ stage: "ingest" })]))).toBe("headIngest");
    expect(headlineKey(match([file({ stage: "analysis", state: "queued" })]))).toBe("headQueued");
    // the first half analysed, the second waits: the analysis runs
    expect(headlineKey(match([file({ stage: "analysis" }), file({ video_id: "v2", stage: "analysis", state: "waiting" })]))).toBe("headAnalysis");
    expect(headlineKey(match([file({ stage: "ingest", state: "stalled" })], { state: "stalled", stage: "ingest" }))).toBe("headStalledIngest");
    expect(headlineKey(match([file({ state: "interrupted" })], { state: "interrupted" }))).toBe("headInterrupted");
    expect(tone({ state: "stalled" })).toBe("attn");
    expect(tone({ state: "failed" })).toBe("fail");
    expect(isActive({ state: "waiting" })).toBe(true);
    expect(isActive({ state: "done" })).toBe(false);
  });

  it("marks the steps of a file", () => {
    const f = file({ stage: "analysis" });
    expect(["upload", "ingest", "analysis", "done"].map((s) => stepState(f, s as "upload"))).toEqual(["done", "done", "now", "next"]);
    expect(stepState(file({ stage: "done", state: "done" }), "done")).toBe("done");
  });
});

describe("the uploads of this tab over the API's view", () => {
  const now = 1_000_000;
  const u = (extra: Partial<LocalUpload> = {}): LocalUpload => ({
    key: "k",
    matchId: "m1",
    videoId: "v1",
    filename: "spiel.mp4",
    done: 500,
    total: 1000,
    startedAt: now - 100_000,
    movedAt: now - 1_000,
    state: "uploading",
    ...extra,
  });

  it("takes the bytes and the pace from this tab", () => {
    const [p] = withLocal([match([file()])], [u()], now);
    expect(p!.files[0]!.fraction).toBe(0.5);
    expect(p!.files[0]!.eta_basis).toBe("measured");
    expect(p!.eta_s).toBe(p!.files[0]!.eta_s);
    expect(localEta(u(), now)).toBe(98); // 500 bytes in 99 s, 500 to go, one second since
  });

  it("says a failed upload here is interrupted, never running and failed at once (L4)", () => {
    const [p] = withLocal([match([file()])], [u({ state: "failed" })], now);
    expect(p!.state).toBe("interrupted");
    expect(p!.files[0]!.state).toBe("interrupted");
    expect(p!.eta_s).toBeNull();
  });

  it("leaves other matches and files alone", () => {
    const other = match([file({ video_id: "v9" })], { match_id: "m2" });
    expect(withLocal([other], [u()], now)).toEqual([other]);
  });
});

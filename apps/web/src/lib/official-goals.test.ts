import { describe, expect, it } from "vitest";
import {
  goalRows,
  isOpen,
  jumpTarget,
  LEAD_MS,
  nextReview,
  withReview,
  type GoalComparison,
} from "./official-goals";

const official = (
  id: string,
  clock_s: number,
  over: Partial<GoalComparison["goals"][number]> = {},
): GoalComparison["goals"][number] => ({
  event_id: id,
  side: "own",
  period: clock_s < 1800 ? 1 : 2,
  clock_s,
  official_time: `${String(Math.floor(clock_s / 60)).padStart(2, "0")}:${String(clock_s % 60).padStart(2, "0")}`,
  t_ms: null,
  estimated: true,
  number: 7,
  player_id: null,
  name: "ZIMMERLI Lisa",
  score: [1, 0],
  penalty: false,
  status: "missing",
  video: null,
  review: null,
  ...over,
});

const cmp: GoalComparison = {
  imported: true,
  provider: "handball_ch",
  source_url: null,
  home: "A",
  away: "B",
  window_s: 20,
  counts: { official: 3, found: 1, missing: 2, extra: 1, open: 3 },
  goals: [
    official("b", 1846, { status: "missing", t_ms: 1_900_000 }),
    official("a", 93, {
      status: "found",
      t_ms: 35_000,
      estimated: false,
      video: {
        source: "scoreboard_ocr",
        t_ms: 35_000,
        clock_s: 95,
        confidence: 0.95,
        event_id: null,
      },
    }),
    official("c", 240, { status: "missing", review: "confirmed" }),
  ],
  extra: [
    {
      event_id: "x",
      side: "opponent",
      period: 1,
      clock_s: 560,
      official_time: "09:20",
      t_ms: 500_000,
      source: "scoreboard_ocr",
      confidence: 0.8,
      number: null,
      player_id: null,
      name: null,
      score: [2, 4],
      review: null,
    },
  ],
};

describe("official goals compared with the video", () => {
  it("lists official and extra goals in match order", () => {
    const rows = goalRows(cmp);
    expect(rows.map((r) => [r.id, r.kind])).toEqual([
      ["a", "found"],
      ["c", "missing"],
      ["x", "extra"],
      ["b", "missing"],
    ]);
    expect(rows[0]!.source).toBe("scoreboard_ocr");
    expect(rows[2]!.estimated).toBe(false);
  });

  it("keeps only the rows still to check", () => {
    expect(goalRows(cmp, "open").map((r) => r.id)).toEqual(["x", "b"]);
    expect(goalRows(cmp).filter(isOpen).length).toBe(cmp.counts.open - 1); // c is confirmed
  });

  it("jumps a little before the goal, never before the start", () => {
    const [a, c, x] = goalRows(cmp);
    expect(jumpTarget(a!)).toBe(35_000 - LEAD_MS);
    expect(jumpTarget(c!)).toBeNull();
    expect(jumpTarget({ ...x!, tMs: 1000 })).toBe(0);
  });

  it("toggles a review and recounts the open rows", () => {
    expect(nextReview(null, "confirmed")).toBe("confirmed");
    expect(nextReview("confirmed", "confirmed")).toBeNull();
    expect(nextReview("confirmed", "dismissed")).toBe("dismissed");
    const after = withReview(cmp, "x", "dismissed");
    expect(after.extra[0]!.review).toBe("dismissed");
    expect(after.counts.open).toBe(1);
    expect(withReview(after, "c", null).counts.open).toBe(2);
    expect(cmp.extra[0]!.review).toBeNull(); // unchanged
  });
});

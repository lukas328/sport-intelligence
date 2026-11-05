import { describe, expect, it } from "vitest";
import {
  focusAfter,
  isOpen,
  keyAction,
  moveFocus,
  visibleRows,
  withReview,
  type Candidate,
  type CandidateList,
} from "./goal-candidates";

const cand = (
  id: string,
  t_ms: number,
  rate: number,
  over: Partial<Candidate> = {},
): Candidate => ({
  id,
  video_asset_id: "v",
  t_ms,
  goal_ms: t_ms - 1500,
  start_ms: t_ms - 10_000,
  end_ms: t_ms + 4000,
  score: 1,
  rate,
  suggested_side: null,
  status: "open",
  side: null,
  event_id: null,
  period: 1,
  clock_s: null,
  known: null,
  ...over,
});

const list = (candidates: Candidate[]): CandidateList => ({
  template: "2026-11-05.1",
  rates: [1, 2, 4],
  default_rate: 2,
  counts: {
    total: candidates.length,
    open: 0,
    open_by_rate: {},
    confirmed: 0,
    rejected: 0,
    known: 0,
  },
  candidates,
});

const known = { event_id: "g", source: "scoreboard_ocr", side: "own", t_ms: 90_000 };
const rows = [
  cand("a", 60_000, 1),
  cand("b", 100_000, 2, { known }),
  cand("c", 150_000, 4),
  cand("d", 200_000, 4, { status: "rejected" }),
  cand("e", 250_000, 2, { status: "confirmed", side: "own", event_id: "x" }),
];

describe("goal candidates", () => {
  it("shows what still needs a click at the chosen rate", () => {
    const l = list(rows);
    expect(visibleRows(l, 2, "open").map((c) => c.id)).toEqual(["a"]);
    expect(visibleRows(l, 4, "open").map((c) => c.id)).toEqual(["a", "c"]);
    // all: the rate's candidates plus everything reviewed, whatever its rate
    expect(visibleRows(l, 2, "all").map((c) => c.id)).toEqual(["a", "b", "d", "e"]);
    expect(visibleRows(l, 1, "all").map((c) => c.id)).toEqual(["a", "d", "e"]);
    expect(isOpen(rows[1]!)).toBe(false);
  });

  it("updates a review optimistically with its counts", () => {
    const l = withReview(list(rows), "a", "confirmed", "opponent");
    expect(l.candidates[0]).toMatchObject({ status: "confirmed", side: "opponent" });
    expect(l.counts).toMatchObject({
      open: 1,
      confirmed: 2,
      rejected: 1,
      open_by_rate: { "1": 0, "2": 0, "4": 1 },
    });
    const undone = withReview(l, "a", null, "own");
    expect(undone.candidates[0]).toMatchObject({ status: "open", side: null });
    expect(withReview(list(rows), "c", "rejected", null).counts).toMatchObject({
      open: 1,
      rejected: 2,
    });
  });

  it("maps keys without the tagger's and the player's letters", () => {
    expect(keyAction("1")).toBe("own");
    expect(keyAction("2")).toBe("opponent");
    expect(keyAction("X")).toBe("reject");
    expect(keyAction("Delete")).toBe("reject");
    expect(keyAction("u")).toBe("undo");
    expect(keyAction("Enter")).toBe("play");
    expect(keyAction("ArrowDown")).toBe("next");
    for (const k of ["g", "s", "m", "p", "t", "k", "j", "l", "f"]) expect(keyAction(k)).toBeNull();
  });

  it("moves the focus to the next row after a review", () => {
    expect(focusAfter(3, 0, true)).toBe(0); // the row left the list: the next one moved up
    expect(focusAfter(3, 2, true)).toBe(1); // the last one: the one before
    expect(focusAfter(1, 0, true)).toBe(-1); // nothing left to look at
    expect(focusAfter(3, 0, false)).toBe(1); // stays in the list: the next one
    expect(focusAfter(3, 2, false)).toBe(2);
    expect(focusAfter(0, 0, true)).toBe(-1);
    expect(moveFocus("next", 2, 3)).toBe(2);
    expect(moveFocus("prev", 0, 3)).toBe(0);
    expect(moveFocus("last", 0, 3)).toBe(2);
    expect(moveFocus("first", 2, 3)).toBe(0);
  });
});

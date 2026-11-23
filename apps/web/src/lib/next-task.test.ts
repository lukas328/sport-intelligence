import { describe, expect, it } from "vitest";
import { nextTask } from "./next-task";

const base = { staff: true, example: false, upcoming: false, hasOpponent: true, running: false, checks: 0, spotsMissing: 0, hasVideo: true, paper: false };

describe("next task of a match page (L5)", () => {
  it("names one task, the most urgent first", () => {
    expect(nextTask({ ...base, checks: 2, spotsMissing: 3 })).toEqual({ kind: "checks", n: 2 });
    expect(nextTask({ ...base, spotsMissing: 3 })).toEqual({ kind: "spots", n: 3 });
    expect(nextTask({ ...base, hasVideo: false })).toEqual({ kind: "upload" });
    expect(nextTask({ ...base, upcoming: true, hasVideo: false })).toEqual({ kind: "prepare" });
  });

  it("says nothing when there is nothing to do or it is not the viewer's job", () => {
    expect(nextTask(base)).toBeNull();
    expect(nextTask({ ...base, staff: false, checks: 2 })).toBeNull();
    expect(nextTask({ ...base, example: true, checks: 2 })).toBeNull();
    expect(nextTask({ ...base, running: true, checks: 2 })).toBeNull();
    expect(nextTask({ ...base, hasVideo: false, paper: true })).toBeNull();
    expect(nextTask({ ...base, upcoming: true, hasOpponent: false })).toBeNull();
  });
});

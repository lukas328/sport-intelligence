import { describe, expect, it } from "vitest";
import { readStageMode, STAGE_MODE_KEY } from "./stage-mode";

const store = (v: string | null) => ({ getItem: (k: string) => (k === STAGE_MODE_KEY ? v : null) });

describe("the stage of the tab Video (app review UX-01)", () => {
  it("starts with the video", () => {
    expect(readStageMode(store(null))).toBe("video");
    expect(readStageMode(null)).toBe("video");
    expect(readStageMode(store("something"))).toBe("video");
  });

  it("keeps the coach's choice of «Feld von oben»", () => {
    expect(readStageMode(store("taktik"))).toBe("taktik");
  });

  it("falls back to the video when the storage cannot be read", () => {
    expect(
      readStageMode({
        getItem: () => {
          throw new Error("blocked");
        },
      }),
    ).toBe("video");
  });
});

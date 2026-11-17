import { TEMPLATES, templateDoc, type PlayDoc } from "@handball/tactics";
import { describe, expect, it } from "vitest";
import { commonFrom, previewFrom } from "./play-preview";

const doc = (xs: number[], court: PlayDoc["court"] = "half"): PlayDoc => ({
  formatVersion: 1,
  court,
  frames: [{ tokens: xs.map((x, i) => ({ id: `t${i}`, side: "own", label: "", x, y: 10 })), ball: null, arrows: [], note: "", duration_ms: 1000 }],
});

describe("previewFrom", () => {
  it("starts in front of the farthest player", () => {
    expect(previewFrom(doc([39, 31.5, 35]))).toBe(29);
  });

  it("has nothing to say for a full court or an empty board", () => {
    expect(previewFrom(doc([30], "full"))).toBeUndefined();
    expect(previewFrom(doc([]))).toBeUndefined();
  });

  it("crops every half-court template nearer than the centre line", () => {
    for (const tpl of TEMPLATES) {
      const d = templateDoc(tpl, "de-CH");
      if (d.court === "half") expect(previewFrom(d), tpl.id).toBeGreaterThan(20);
    }
  });

  it("lines a grid up on the farthest start", () => {
    expect(commonFrom([doc([39, 33]), doc([36]), doc([30], "full")])).toBe(31);
    expect(commonFrom([doc([])])).toBeUndefined();
  });
});

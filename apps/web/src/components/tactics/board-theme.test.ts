import { describe, expect, it } from "vitest";
import { contrastRatio, luminance } from "@/lib/color";
import { BOARD_THEME as T, simplify } from "./board-theme";

describe("board theme (K23)", () => {
  it("numbers on the players read like text (4.5:1)", () => {
    expect(contrastRatio(T.ownText, T.own)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(T.oppText, T.opp)).toBeGreaterThanOrEqual(4.5);
  });

  it("lines, arrows and rims stand out on the floor and in the goal area (3:1)", () => {
    for (const ground of [T.floor, T.goalArea, T.surround]) {
      expect(contrastRatio(T.line, ground), ground).toBeGreaterThanOrEqual(7);
      expect(contrastRatio(T.rim, ground), ground).toBeGreaterThanOrEqual(3);
    }
    // the rim around the ball and the players is dark enough against the ball and the opponents
    expect(contrastRatio(T.rim, T.ball)).toBeGreaterThanOrEqual(3);
    expect(contrastRatio(T.rim, T.opp)).toBeGreaterThanOrEqual(3);
  });

  it("own and opponent players differ in lightness, not only in hue (colour-blind safe)", () => {
    expect(contrastRatio(T.own, T.opp)).toBeGreaterThanOrEqual(3);
    expect(luminance(T.opp)).toBeGreaterThan(luminance(T.own));
    // the own blue is clearly darker than the floor, the ball clearly lighter than the own blue
    expect(contrastRatio(T.own, T.floor)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(T.ball, T.own)).toBeGreaterThanOrEqual(3);
  });

  it("keeps a drawn run to twelve points", () => {
    const wiggle = Array.from({ length: 80 }, (_, i) => [20 + i * 0.2, 10 + Math.sin(i / 3) * 2] as [number, number]);
    const out = simplify(wiggle);
    expect(out.length).toBeLessThanOrEqual(12);
    expect(out[0]).toEqual(wiggle[0]);
    expect(out[out.length - 1]).toEqual(wiggle[wiggle.length - 1]);
    expect(simplify([[0, 0], [1, 1]])).toHaveLength(2);
  });
});

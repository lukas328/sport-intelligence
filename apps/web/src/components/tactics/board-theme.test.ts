import { describe, expect, it } from "vitest";
import { contrastRatio, luminance } from "@/lib/color";
import { BOARD_THEME as T, boardColours, passReceiver, simplify } from "./board-theme";

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

describe("players in the club colour (A16, under K23)", () => {
  const CLUBS = ["#157a3a", "#c8102e", "#8a1538", "#b35900", "#1d4ed8", "#173a73", "#5b2d8e", "#17191c", "#ffd200", "#ffffff", "#f39a3a", "#e5e5e5"];
  for (const club of CLUBS) {
    it(`${club}: marks, numbers and the two teams stay apart`, () => {
      const c = boardColours(club);
      expect(contrastRatio(c.own, T.floor)).toBeGreaterThanOrEqual(3);
      expect(contrastRatio(c.ownText, c.own)).toBeGreaterThanOrEqual(4.5);
      expect(contrastRatio(c.oppText, c.opp)).toBeGreaterThanOrEqual(4.5);
      expect(contrastRatio(c.own, c.opp)).toBeGreaterThanOrEqual(3);
      expect(luminance(c.opp)).toBeGreaterThan(luminance(c.own));
    });
  }

  it("takes the club colour as it is when it meets the rules, else the board's blue", () => {
    expect(boardColours("#157a3a").own).toBe("#157a3a");
    expect(boardColours(null).own).toBe(T.own);
    expect(boardColours("#ffffff").own).toBe(T.own);
    // an orange club: the opponent is no longer orange
    expect(boardColours("#b35900").opp).not.toBe(T.opp);
  });
});

describe("a pass reaches a teammate (A16)", () => {
  const tokens = [
    { id: "a", side: "own", x: 30, y: 10 },
    { id: "b", side: "own", x: 34, y: 4 },
    { id: "c", side: "own", x: 34, y: 16 },
    { id: "x", side: "opp", x: 36, y: 5 },
  ];
  it("snaps to the passer's teammate nearest to where it was let go", () => {
    expect(passReceiver([30, 10], [35, 6], tokens)?.id).toBe("b");
    expect(passReceiver([30, 10], [33, 13], tokens)?.id).toBe("c");
  });
  it("never to the passer or an opponent, even let go on them", () => {
    expect(passReceiver([30, 10], [36, 5], tokens)?.id).toBe("b");
    expect(passReceiver([30, 10], [30.2, 10], tokens)?.id).not.toBe("a");
  });
  it("without a teammate nobody", () => {
    expect(passReceiver([30, 10], [35, 6], [tokens[0]!, tokens[3]!])).toBeNull();
  });
});

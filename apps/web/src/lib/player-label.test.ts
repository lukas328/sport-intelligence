import { describe, expect, it } from "vitest";
import { rowLabel } from "./player-label";

const words = { keeper: "Torhüter", player: "Spieler" };
const row = { side: "own" as const, player_id: null, number: null };

describe("rowLabel", () => {
  it("prefers the name, without its number", () => {
    expect(rowLabel({ ...row, player_id: "a", number: 9 }, { a: "#9 Lena Muster" }, words)).toBe("Lena Muster");
  });
  it("takes the paper sheet's name for an own number, else the number", () => {
    expect(rowLabel({ ...row, number: 7 }, {}, words, { "7": "Mia Rot" })).toBe("Mia Rot");
    expect(rowLabel({ ...row, side: "opponent", number: 7 }, {}, words, { "7": "Mia Rot" })).toBe("#7");
  });
  it("never shows #? for a row without a number", () => {
    expect(rowLabel({ ...row, player_id: "gk", saves: 4 }, {}, words)).toBe("Torhüter");
    expect(rowLabel({ ...row, player_id: "x", shots: 2, saves: 0 }, {}, words)).toBe("Spieler");
  });
});

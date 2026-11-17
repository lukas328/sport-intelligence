import { describe, expect, it } from "vitest";
import { findTeamRow, opponentKey, sameOpponent } from "./opponent-name";

describe("opponentKey", () => {
  it("drops case, accents, punctuation and a bracketed addition", () => {
    expect(opponentKey("SG Felsegg/Lärchenwil (M2)")).toBe("sgfelsegglarchenwil");
    expect(opponentKey("sg felsegg-lärchenwil")).toBe("sgfelsegglarchenwil");
  });

  it("treats the first team like the club, a second team as its own", () => {
    expect(opponentKey("SG Felsegg/Lärchenwil 1")).toBe("sgfelsegglarchenwil");
    expect(opponentKey("SG Felsegg/Lärchenwil 2")).toBe("sgfelsegglarchenwil2");
    expect(opponentKey("HC 11 Freunde")).toBe("hc11freunde");
  });

  it("is empty for no name", () => {
    expect(opponentKey(null)).toBe("");
    expect(opponentKey(" (M2) ")).toBe("");
  });
});

describe("sameOpponent", () => {
  it("matches the variants of one team (R7)", () => {
    expect(sameOpponent("SG Felsegg/Lärchenwil 1", "SG Felsegg/Lärchenwil (M2)")).toBe(true);
    expect(sameOpponent("TV Mürli", "TV Murli")).toBe(true);
  });

  it("keeps different teams apart", () => {
    expect(sameOpponent("SG Felsegg/Lärchenwil 1", "SG Felsegg/Lärchenwil 2")).toBe(false);
    expect(sameOpponent("", "")).toBe(false);
  });
});

describe("findTeamRow", () => {
  const rows = [{ name: "HC Farnwil" }, { name: "HC Farnwil 2" }, { name: "SG Felsegg/Lärchenwil" }, { name: "TV Mürli" }];

  it("prefers the same key", () => {
    expect(findTeamRow(rows, "HC Farnwil 1")).toBe(rows[0]);
    expect(findTeamRow(rows, "SG Felsegg/Lärchenwil (M2)")).toBe(rows[2]);
  });

  it("takes a shortened name only when one row fits", () => {
    expect(findTeamRow(rows, "TV Mürli Handball")).toBe(rows[3]);
    expect(findTeamRow([{ name: "HC Farnwil 2" }, { name: "HC Farnwil 3" }], "HC Farnwil")).toBeUndefined();
  });

  it("finds nothing without a name", () => {
    expect(findTeamRow(rows, "")).toBeUndefined();
  });
});

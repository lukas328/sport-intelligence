import { describe, expect, it } from "vitest";
import { findTeamRow, opponentKey, sameOpponent } from "./opponent-name";

describe("opponentKey", () => {
  it("drops case, accents, punctuation and a bracketed addition", () => {
    expect(opponentKey("SG Horgen/Wädenswil (M2)")).toBe("sghorgenwadenswil");
    expect(opponentKey("sg horgen-wädenswil")).toBe("sghorgenwadenswil");
  });

  it("treats the first team like the club, a second team as its own", () => {
    expect(opponentKey("SG Horgen/Wädenswil 1")).toBe("sghorgenwadenswil");
    expect(opponentKey("SG Horgen/Wädenswil 2")).toBe("sghorgenwadenswil2");
    expect(opponentKey("HC 11 Freunde")).toBe("hc11freunde");
  });

  it("is empty for no name", () => {
    expect(opponentKey(null)).toBe("");
    expect(opponentKey(" (M2) ")).toBe("");
  });
});

describe("sameOpponent", () => {
  it("matches the variants of one team (R7)", () => {
    expect(sameOpponent("SG Horgen/Wädenswil 1", "SG Horgen/Wädenswil (M2)")).toBe(true);
    expect(sameOpponent("TV Rüti", "TV Ruti")).toBe(true);
  });

  it("keeps different teams apart", () => {
    expect(sameOpponent("SG Horgen/Wädenswil 1", "SG Horgen/Wädenswil 2")).toBe(false);
    expect(sameOpponent("", "")).toBe(false);
  });
});

describe("findTeamRow", () => {
  const rows = [{ name: "HC Thalwil" }, { name: "HC Thalwil 2" }, { name: "SG Horgen/Wädenswil" }, { name: "TV Rüti" }];

  it("prefers the same key", () => {
    expect(findTeamRow(rows, "HC Thalwil 1")).toBe(rows[0]);
    expect(findTeamRow(rows, "SG Horgen/Wädenswil (M2)")).toBe(rows[2]);
  });

  it("takes a shortened name only when one row fits", () => {
    expect(findTeamRow(rows, "TV Rüti Handball")).toBe(rows[3]);
    expect(findTeamRow([{ name: "HC Thalwil 2" }, { name: "HC Thalwil 3" }], "HC Thalwil")).toBeUndefined();
  });

  it("finds nothing without a name", () => {
    expect(findTeamRow(rows, "")).toBeUndefined();
  });
});

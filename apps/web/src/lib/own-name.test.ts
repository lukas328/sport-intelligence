import { describe, expect, it } from "vitest";
import { clubNameShown, headName, ownName } from "./own-name";

describe("ownName", () => {
  it("takes the team's own name, the club's for a generic team name", () => {
    expect(ownName("SG Lärchenwil/Felsegg", "HC Lärchenwil")).toBe("SG Lärchenwil/Felsegg");
    expect(ownName("Herren 1", "HC Tannengrün")).toBe("HC Tannengrün");
    expect(ownName("U17 Juniorinnen", "HC Tannengrün")).toBe("HC Tannengrün");
    expect(ownName(null, "HC Tannengrün")).toBe("HC Tannengrün");
  });
});

describe("headName", () => {
  it("drops additions in brackets and lets a line break after a slash (UX test A01)", () => {
    expect(headName("SG Lärchenwil/Felsegg")).toBe("SG Lärchenwil/​Felsegg");
    expect(headName("HC Tannengrün (Herren)")).toBe("HC Tannengrün");
    expect(headName("BSV Sälmatt-Uferholz")).toBe("BSV Sälmatt-​Uferholz");
  });
});

describe("clubNameShown (K7)", () => {
  it("leaves the club out when the team already says it", () => {
    expect(clubNameShown("TV Farnwil", "TV Farnwil")).toBeNull();
    expect(clubNameShown("TV Farnwil", "tv farnwil")).toBeNull();
    expect(clubNameShown("TV Farnwil", "TV Farnwil 2")).toBeNull();
    expect(clubNameShown("SG Lärchenwil/Felsegg", "SG Laerchenwil Felsegg")).toBe("SG Lärchenwil/Felsegg");
    expect(clubNameShown("HC Tannengrün", "Herren 1")).toBe("HC Tannengrün");
    expect(clubNameShown("TV Farnwil", null)).toBe("TV Farnwil");
    expect(clubNameShown("TV Farn", "TV Farnwil")).toBe("TV Farn");
  });
});

import { describe, expect, it } from "vitest";
import { clubNameShown, clubTeam, headName, ownName } from "./own-name";

describe("ownName", () => {
  it("takes the team's own name, the club's for a generic team name", () => {
    expect(ownName("SG Lärchenwil/Kalvenegg", "HC Lärchenwil")).toBe("SG Lärchenwil/Kalvenegg");
    expect(ownName("Herren 1", "HC Tannengrün")).toBe("HC Tannengrün");
    expect(ownName("U17 Juniorinnen", "HC Tannengrün")).toBe("HC Tannengrün");
    expect(ownName(null, "HC Tannengrün")).toBe("HC Tannengrün");
  });
});

describe("headName", () => {
  it("drops additions in brackets and lets a line break after a slash (UX test A01)", () => {
    expect(headName("SG Lärchenwil/Kalvenegg")).toBe("SG Lärchenwil/​Kalvenegg");
    expect(headName("HC Tannengrün (Herren)")).toBe("HC Tannengrün");
    expect(headName("BSV Sälmatt-Uferholz")).toBe("BSV Sälmatt-​Uferholz");
  });
});

describe("clubNameShown (K7)", () => {
  it("leaves the club out when the team already says it", () => {
    expect(clubNameShown("TV Farnwil", "TV Farnwil")).toBeNull();
    expect(clubNameShown("TV Farnwil", "tv farnwil")).toBeNull();
    expect(clubNameShown("TV Farnwil", "TV Farnwil 2")).toBeNull();
    expect(clubNameShown("SG Lärchenwil/Kalvenegg", "SG Laerchenwil Kalvenegg")).toBe("SG Lärchenwil/Kalvenegg");
    expect(clubNameShown("HC Tannengrün", "Herren 1")).toBe("HC Tannengrün");
    expect(clubNameShown("TV Farnwil", null)).toBe("TV Farnwil");
    expect(clubNameShown("TV Farn", "TV Farnwil")).toBe("TV Farn");
  });
});

describe("clubTeam (A5)", () => {
  it("names club and team once each", () => {
    expect(clubTeam("TV Farnwil", "Herren 1")).toBe("TV Farnwil Herren 1");
    expect(clubTeam("TV Farnwil", "TV Farnwil")).toBe("TV Farnwil");
    expect(clubTeam("TV Farnwil", "TV Farnwil 2")).toBe("TV Farnwil 2");
    expect(clubTeam(undefined, "Herren 1")).toBe("Herren 1");
    expect(clubTeam("TV Farnwil", null)).toBe("TV Farnwil");
  });
});

import { describe, expect, it } from "vitest";
import { clubNameShown, headName, ownName } from "./own-name";

describe("ownName", () => {
  it("takes the team's own name, the club's for a generic team name", () => {
    expect(ownName("SG Wädenswil/Horgen", "HC Wädenswil")).toBe("SG Wädenswil/Horgen");
    expect(ownName("Herren 1", "HC Zürichsee")).toBe("HC Zürichsee");
    expect(ownName("U17 Juniorinnen", "HC Zürichsee")).toBe("HC Zürichsee");
    expect(ownName(null, "HC Zürichsee")).toBe("HC Zürichsee");
  });
});

describe("headName", () => {
  it("drops additions in brackets and lets a line break after a slash (UX test A01)", () => {
    expect(headName("SG Wädenswil/Horgen")).toBe("SG Wädenswil/​Horgen");
    expect(headName("HC Zürichsee (Herren)")).toBe("HC Zürichsee");
    expect(headName("BSV Stäfa-Uerikon")).toBe("BSV Stäfa-​Uerikon");
  });
});

describe("clubNameShown (K7)", () => {
  it("leaves the club out when the team already says it", () => {
    expect(clubNameShown("TV Thalwil", "TV Thalwil")).toBeNull();
    expect(clubNameShown("TV Thalwil", "tv thalwil")).toBeNull();
    expect(clubNameShown("TV Thalwil", "TV Thalwil 2")).toBeNull();
    expect(clubNameShown("SG Wädenswil/Horgen", "SG Waedenswil Horgen")).toBe("SG Wädenswil/Horgen");
    expect(clubNameShown("HC Zürichsee", "Herren 1")).toBe("HC Zürichsee");
    expect(clubNameShown("TV Thalwil", null)).toBe("TV Thalwil");
    expect(clubNameShown("TV Thal", "TV Thalwil")).toBe("TV Thal");
  });
});

import { describe, expect, it } from "vitest";
import { headName, ownName } from "./own-name";

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

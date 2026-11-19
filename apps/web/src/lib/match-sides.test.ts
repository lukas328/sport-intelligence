import { describe, expect, it } from "vitest";
import { homeFirst, matchSides, pairing, perspectiveOf, sideLabel } from "./match-sides";

const names = { team: "TV Thalwil", opponent: "Handball Mülheim Urmit", otherFallback: "Gegner des Gegners" };

describe("perspective of a match (app review BUG-01 to 07)", () => {
  it("is ours for a match of the team, neutral for an observed one", () => {
    expect(perspectiveOf({ kind: "match" })).toBe("own");
    expect(perspectiveOf({ kind: "training" })).toBe("own");
    expect(perspectiveOf({ kind: "scouting" })).toBe("neutral");
  });

  it("never names the account team in an observed match", () => {
    const s = matchSides({ kind: "scouting", scouting_other: "südpfalz tiger", is_home: true }, names);
    expect(s.neutral).toBe(true);
    expect(s.own).toBe("südpfalz tiger");
    expect(s.opp).toBe("Handball Mülheim Urmit");
    expect(pairing(s, "gegen")).toBe("südpfalz tiger gegen Handball Mülheim Urmit");
    expect(JSON.stringify(s)).not.toContain("TV Thalwil");
    // nobody is «Wir»: both teams by name
    expect(sideLabel(s, "own", "Wir")).toBe("südpfalz tiger");
    expect(sideLabel(s, "opp", "Wir")).toBe("Handball Mülheim Urmit");
  });

  it("falls back to a word, not to our team, while the other team has no name", () => {
    const s = matchSides({ kind: "scouting", scouting_other: " ", is_home: true }, names);
    expect(s.own).toBe("Gegner des Gegners");
  });

  it("keeps «Wir» and our name in a match of the team", () => {
    const s = matchSides({ kind: "match", is_home: true }, names);
    expect(s.neutral).toBe(false);
    expect(s.own).toBe("TV Thalwil");
    expect(sideLabel(s, "own", "Wir")).toBe("Wir");
  });

  it("puts the home team first everywhere (BUG-18)", () => {
    const away = matchSides({ kind: "match", is_home: false }, names);
    expect(pairing(away, "gegen")).toBe("Handball Mülheim Urmit gegen TV Thalwil");
    expect(homeFirst(away, "own", "opp")).toEqual(["opp", "own"]);
    const home = matchSides({ kind: "scouting", scouting_other: "HC Dritte", is_home: true }, names);
    expect(homeFirst(home, 1, 2)).toEqual([1, 2]);
  });
});

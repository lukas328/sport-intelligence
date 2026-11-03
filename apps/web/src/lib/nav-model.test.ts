import { describe, expect, it } from "vitest";
import { destOf, modeFor, navFor, teamInPath, teamSectionOf, trainingSectionOf } from "./nav-model";

const T = "11111111-2222-3333-4444-555555555555";

describe("navigation model", () => {
  it("derives the mode from the roles", () => {
    expect(modeFor("org_admin", null)).toBe("staff");
    expect(modeFor("member", "coach")).toBe("staff");
    expect(modeFor("member", "goalkeeper")).toBe("player");
    expect(modeFor("member", "parent")).toBe("family");
    expect(modeFor("member", "guest")).toBe("guest");
  });

  it("never offers more than four destinations", () => {
    for (const m of ["staff", "player", "family", "guest"] as const) {
      expect(navFor(m, "o", T).length).toBeLessThanOrEqual(4);
      expect(navFor(m, "o", null)[0]?.key).toBe("today");
    }
    expect(navFor("staff", "o", T).map((i) => i.key)).toEqual(["today", "matches", "team", "training"]);
    expect(navFor("player", "o", T).map((i) => i.key)).toEqual(["today", "scenes", "dates", "team"]);
  });

  it("keeps the destination highlighted on pages below it", () => {
    expect(destOf("/app/o", "staff")).toBe("today");
    expect(destOf(`/app/o/teams/${T}`, "staff")).toBe("team");
    expect(destOf(`/app/o/teams/${T}/matrix`, "staff")).toBe("team");
    expect(destOf("/app/o/matches/x/live", "staff")).toBe("matches");
    expect(destOf("/app/o/playlists/x", "staff")).toBe("team");
    expect(destOf("/app/o/drills", "staff")).toBe("training");
    expect(destOf("/app/o/schedule", "player")).toBe("dates");
    expect(destOf("/app/o/feed/x", "player")).toBe("scenes");
    expect(destOf("/app/o/settings", "staff")).toBeNull();
  });

  it("finds sub sections and the team", () => {
    expect(teamSectionOf(`/app/o/teams/${T}`)).toBe("roster");
    expect(teamSectionOf(`/app/o/teams/${T}/assistant`)).toBe("season");
    expect(teamSectionOf("/app/o/plays/x")).toBe("library");
    expect(trainingSectionOf("/app/o/drills")).toBe("drills");
    expect(trainingSectionOf(`/app/o/teams/${T}/assignments`)).toBe("assignments");
    expect(teamInPath(`/app/o/teams/${T}/season`)).toBe(T);
    expect(teamInPath("/app/o")).toBeNull();
  });
});

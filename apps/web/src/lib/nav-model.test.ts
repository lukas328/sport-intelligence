import { describe, expect, it } from "vitest";
import { destOf, modeFor, navFor, sectionOf, sectionsFor, teamInPath } from "./nav-model";

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
    expect(navFor("staff", "o", T).map((i) => i.key)).toEqual(["today", "matches", "training", "team"]);
    expect(navFor("player", "o", T).map((i) => i.key)).toEqual(["today", "scenes", "dates", "team"]);
  });

  it("keeps the destination highlighted on pages below it", () => {
    expect(destOf("/app/o", "staff")).toBe("today");
    expect(destOf(`/app/o/teams/${T}`, "staff")).toBe("team");
    expect(destOf(`/app/o/teams/${T}/matrix`, "staff")).toBe("matches");
    expect(destOf(`/app/o/teams/${T}/season`, "staff")).toBe("matches");
    expect(destOf(`/app/o/teams/${T}/season`, "player")).toBe("team");
    expect(destOf(`/app/o/teams/${T}/plays`, "staff")).toBe("training");
    expect(destOf("/app/o/schedule", "staff")).toBe("team");
    expect(destOf("/app/o/matches/x/live", "staff")).toBe("matches");
    expect(destOf("/app/o/playlists/x", "staff")).toBe("matches");
    expect(destOf("/app/o/drills", "staff")).toBe("training");
    expect(destOf("/app/o/schedule", "player")).toBe("dates");
    expect(destOf("/app/o/feed/x", "player")).toBe("scenes");
    expect(destOf("/app/o/settings", "staff")).toBeNull();
  });

  it("finds sub sections and the team", () => {
    expect(sectionOf(`/app/o/teams/${T}`)).toBe("roster");
    expect(sectionOf(`/app/o/teams/${T}/matches`)).toBe("fixtures");
    expect(sectionOf(`/app/o/teams/${T}/assistant`)).toBe("season");
    expect(sectionOf("/app/o/playlists/x")).toBe("library");
    expect(sectionOf("/app/o/plays/x")).toBe("plays");
    expect(sectionOf("/app/o/drills")).toBe("drills");
    expect(sectionOf("/app/o/schedule")).toBe("dates");
    expect(sectionOf(`/app/o/teams/${T}/assignments`)).toBe("assignments");
    expect(sectionOf("/app/o/settings")).toBeNull();
    expect(teamInPath(`/app/o/teams/${T}/season`)).toBe(T);
    expect(teamInPath("/app/o")).toBeNull();
  });

  it("groups the second level by the coach's jobs, never more than four items", () => {
    expect(sectionsFor("matches", "staff", "o", T).map((i) => i.key)).toEqual(["fixtures", "season", "library"]);
    expect(sectionsFor("training", "staff", "o", T).map((i) => i.key)).toEqual(["plan", "drills", "plays", "assignments"]);
    expect(sectionsFor("team", "staff", "o", T).map((i) => i.key)).toEqual(["roster", "dates"]);
    expect(sectionsFor("team", "player", "o", T).map((i) => i.key)).toEqual(["roster", "season"]);
    expect(sectionsFor("matches", "guest", "o", T)).toEqual([]);
    for (const d of ["today", "matches", "training", "team", "scenes", "dates"] as const)
      for (const m of ["staff", "player", "family", "guest"] as const) expect(sectionsFor(d, m, "o", T).length).toBeLessThanOrEqual(4);
    expect(sectionsFor("training", "player", "o", T)).toEqual([]);
    expect(sectionsFor("today", "staff", "o", T)).toEqual([]);
  });

  it("keeps the squad highlighted on the official data and the join requests, and fixtures on an opponent", () => {
    const team = "/app/o/teams/00000000-0000-4000-8000-000000000001";
    expect(destOf(`${team}/official`, "staff")).toBe("team");
    expect(sectionOf(`${team}/official`)).toBe("roster");
    expect(destOf(`${team}/join-requests`, "staff")).toBe("team");
    expect(sectionOf(`${team}/join-requests`)).toBe("roster");
    expect(destOf("/app/o/opponents/x", "staff")).toBe("matches");
    expect(sectionOf("/app/o/opponents/x")).toBe("fixtures");
  });
});

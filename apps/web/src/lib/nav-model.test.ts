import { describe, expect, it } from "vitest";
import { destOf, modeFor, navFor, sectionOf, sectionsFor, startHref, teamInPath, uploadHref } from "./nav-model";

const T = "11111111-2222-3333-4444-555555555555";
const TEAM = `/app/o/teams/${T}`;

describe("navigation model", () => {
  it("derives the mode from the roles", () => {
    expect(modeFor("org_admin", null)).toBe("staff");
    expect(modeFor("member", "coach")).toBe("staff");
    expect(modeFor("member", "analyst")).toBe("staff");
    expect(modeFor("member", "team_manager")).toBe("staff");
    expect(modeFor("member", "goalkeeper")).toBe("player");
    expect(modeFor("member", "parent")).toBe("family");
    expect(modeFor("member", "guest")).toBe("guest");
  });

  it("gives staff four destinations, Spiele first (SPEC section 6)", () => {
    expect(navFor("staff", "o", T).map((i) => i.key)).toEqual(["matches", "scenes", "season", "team"]);
    expect(navFor("staff", "o", T).map((i) => i.href)).toEqual([`${TEAM}/matches`, `${TEAM}/scenes`, `${TEAM}/season`, TEAM]);
    // a club without a team yet still has its start
    expect(navFor("staff", "o", null)).toEqual([{ key: "matches", href: "/app/o" }]);
    for (const m of ["staff", "player", "family", "guest"] as const) {
      expect(navFor(m, "o", T).length).toBeLessThanOrEqual(4);
      expect(navFor(m, "o", null).length).toBeGreaterThan(0);
    }
    expect(navFor("guest", "o", T).map((i) => i.key)).toEqual(["matches", "team"]);
  });

  it("starts staff on Spiele and offers the upload everywhere", () => {
    expect(startHref("staff", "o", T)).toBe(`${TEAM}/matches`);
    expect(startHref("staff", "o", null)).toBe("/app/o");
    expect(startHref("player", "o", T)).toBe("/app/o");
    expect(uploadHref("o", T)).toBe(`${TEAM}/matches?upload=1`);
    expect(uploadHref("o", null)).toBeNull();
  });

  it("keeps the destination highlighted on pages below it", () => {
    expect(destOf("/app/o", "staff")).toBe("matches");
    expect(destOf("/app/o", "player")).toBe("today");
    expect(destOf(TEAM, "staff")).toBe("team");
    expect(destOf("/app/o/matches/x/live", "staff")).toBe("matches");
    expect(destOf(`${TEAM}/paper`, "staff")).toBe("matches");
    for (const p of ["scenes", "search", "assistant", "library", "matrix", "plays", "playlists"]) expect(destOf(`${TEAM}/${p}`, "staff")).toBe("scenes");
    expect(destOf("/app/o/playlists/x", "staff")).toBe("scenes");
    expect(destOf("/app/o/presentations/x", "staff")).toBe("scenes");
    expect(destOf("/app/o/plays/x", "staff")).toBe("scenes");
    expect(destOf(`${TEAM}/season`, "staff")).toBe("season");
    expect(destOf("/app/o/opponents/x", "staff")).toBe("season");
    expect(destOf(`${TEAM}/season`, "player")).toBe("team");
    // out of the navigation for staff, still reachable: kept under Team
    expect(destOf(`${TEAM}/training`, "staff")).toBe("team");
    expect(destOf("/app/o/drills", "staff")).toBe("team");
    expect(destOf("/app/o/schedule", "staff")).toBe("team");
    expect(destOf("/app/o/schedule", "player")).toBe("dates");
    expect(destOf("/app/o/feed/x", "player")).toBe("scenes");
    expect(destOf("/app/o/settings", "staff")).toBeNull();
    expect(destOf("/app/o/me/security", "staff")).toBeNull();
    expect(destOf("/app/o/club/teams", "staff")).toBeNull();
    expect(destOf(`${TEAM}/collections`, "staff")).toBe("scenes");
    expect(destOf("/app/o/matches/x/matchday", "staff")).toBe("matches");
  });

  it("finds the tab and the team", () => {
    expect(sectionOf(TEAM)).toBe("roster");
    expect(sectionOf(`${TEAM}/matches`)).toBe("fixtures");
    expect(sectionOf(`${TEAM}/scenes`)).toBe("scenes");
    expect(sectionOf(`${TEAM}/assistant`)).toBe("scenes");
    expect(sectionOf(`${TEAM}/library`)).toBe("collections");
    expect(sectionOf("/app/o/playlists/x")).toBe("collections");
    expect(sectionOf("/app/o/plays/x")).toBe("plays");
    expect(sectionOf(`${TEAM}/matrix`)).toBe("matrix");
    expect(sectionOf("/app/o/schedule")).toBe("dates");
    expect(sectionOf("/app/o/settings")).toBeNull();
    expect(teamInPath(`${TEAM}/season`)).toBe(T);
    expect(teamInPath("/app/o")).toBeNull();
  });

  it("has at most one level of tabs with at most four items", () => {
    expect(sectionsFor("scenes", "staff", "o", T).map((i) => i.key)).toEqual(["scenes", "collections", "plays", "matrix"]);
    expect(sectionsFor("scenes", "staff", "o", T)[1]?.href).toBe(`${TEAM}/collections`);
    // a single tab is no tab
    for (const d of ["matches", "season", "team"] as const) expect(sectionsFor(d, "staff", "o", T)).toEqual([]);
    expect(sectionsFor("team", "player", "o", T).map((i) => i.key)).toEqual(["roster", "season"]);
    for (const d of ["today", "matches", "scenes", "season", "team", "dates"] as const)
      for (const m of ["staff", "player", "family", "guest"] as const) expect(sectionsFor(d, m, "o", T).length).toBeLessThanOrEqual(4);
  });

  it("hides training, dates, tasks and the player and parent destinations unless Teamfunktionen is on", () => {
    const on = { teamFunctions: true };
    // staff: the same four destinations either way; the team features become tabs of Team
    expect(navFor("staff", "o", T, on).map((i) => i.key)).toEqual(["matches", "scenes", "season", "team"]);
    expect(sectionsFor("team", "staff", "o", T, on).map((i) => i.key)).toEqual(["roster", "dates", "plan", "assignments"]);
    expect(sectionsFor("team", "staff", "o", T)).toEqual([]);
    // players and parents: their own scenes and the dates only with the setting
    expect(navFor("player", "o", T).map((i) => i.key)).toEqual(["today", "team"]);
    expect(navFor("player", "o", T, on).map((i) => i.key)).toEqual(["today", "scenes", "dates", "team"]);
    expect(navFor("family", "o", T).map((i) => i.key)).toEqual(["today", "team"]);
    expect(navFor("family", "o", T, on).map((i) => i.key)).toEqual(["today", "dates", "team"]);
    // the routes stay reachable and keep a destination
    expect(destOf(`${TEAM}/training`, "staff")).toBe("team");
    expect(sectionOf(`${TEAM}/training`)).toBe("plan");
    expect(sectionOf(`${TEAM}/assignments`)).toBe("assignments");
  });

  it("keeps the squad highlighted on the official data, join requests and a player's line", () => {
    for (const p of ["official", "join-requests", "players/x"]) {
      expect(destOf(`${TEAM}/${p}`, "staff")).toBe("team");
      expect(sectionOf(`${TEAM}/${p}`)).toBe("roster");
    }
  });
});

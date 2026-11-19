import { describe, expect, it } from "vitest";
import { analyses, destOf, lifeHref, modeFor, navFor, sectionOf, sectionsFor, startHref, teamInPath, uploadHref, videoWork } from "./nav-model";

const T = "11111111-2222-3333-4444-555555555555";
const TEAM = `/app/o/teams/${T}`;
const MODES = ["staff", "player", "family", "guest"] as const;
const DESTS = ["matches", "scenes", "season", "team", "life"] as const;

describe("navigation model", () => {
  it("derives the mode from the roles (K18: the Co-Trainer roles are staff)", () => {
    expect(modeFor("org_admin", null)).toBe("staff");
    for (const r of ["coach", "analyst", "team_manager", "goalkeeper_coach", "athletic_coach"]) expect(modeFor("member", r)).toBe("staff");
    expect(modeFor("member", "goalkeeper")).toBe("player");
    expect(modeFor("member", "player")).toBe("player");
    expect(modeFor("member", "parent")).toBe("family");
    expect(modeFor("member", "guest")).toBe("guest");
    expect(videoWork("member", "player")).toBe(true);
    expect(videoWork("member", "parent")).toBe(false);
    expect(analyses("player")).toBe(true);
    expect(analyses("family")).toBe(false);
  });

  it("gives staff and players four destinations, Spiele first (SPEC section 6, K18)", () => {
    for (const m of ["staff", "player"] as const) {
      expect(navFor(m, "o", T).map((i) => i.key)).toEqual(["matches", "scenes", "season", "team"]);
      expect(navFor(m, "o", T).map((i) => i.href)).toEqual([`${TEAM}/matches`, `${TEAM}/scenes`, `${TEAM}/season`, TEAM]);
    }
    // a club without a team yet still has its start
    expect(navFor("staff", "o", null)).toEqual([{ key: "matches", href: "/app/o" }]);
    for (const m of MODES) {
      expect(navFor(m, "o", T).length).toBeLessThanOrEqual(4);
      expect(navFor(m, "o", T, { teamFunctions: true }).length).toBeLessThanOrEqual(5);
      expect(navFor(m, "o", null).length).toBeGreaterThan(0);
    }
    expect(navFor("guest", "o", T).map((i) => i.key)).toEqual(["matches", "team"]);
    expect(navFor("family", "o", T).map((i) => i.key)).toEqual(["life"]);
  });

  it("starts everyone in the team on Spiele, parents on Teamleben, and offers the upload", () => {
    expect(startHref("staff", "o", T)).toBe(`${TEAM}/matches`);
    expect(startHref("player", "o", T)).toBe(`${TEAM}/matches`);
    expect(startHref("staff", "o", null)).toBe("/app/o");
    expect(startHref("family", "o", T)).toBe("/app/o");
    expect(uploadHref("o", T)).toBe(`${TEAM}/matches?upload=1`);
    expect(uploadHref("o", null)).toBeNull();
  });

  it("keeps the destination highlighted on pages below it", () => {
    expect(destOf("/app/o", "staff")).toBe("matches");
    expect(destOf("/app/o", "family")).toBe("life");
    expect(destOf(TEAM, "staff")).toBe("team");
    expect(destOf(TEAM, "player")).toBe("team");
    expect(destOf("/app/o/matches/x/live", "staff")).toBe("matches");
    expect(destOf("/app/o/matches/x", "player")).toBe("matches");
    expect(destOf(`${TEAM}/paper`, "staff")).toBe("matches");
    for (const p of ["scenes", "search", "assistant", "library", "matrix", "plays", "playlists"]) {
      expect(destOf(`${TEAM}/${p}`, "staff")).toBe("scenes");
      expect(destOf(`${TEAM}/${p}`, "player")).toBe("scenes");
    }
    expect(destOf("/app/o/playlists/x", "staff")).toBe("scenes");
    expect(destOf("/app/o/presentations/x", "staff")).toBe("scenes");
    expect(destOf("/app/o/plays/x", "staff")).toBe("scenes");
    expect(destOf(`${TEAM}/season`, "staff")).toBe("season");
    expect(destOf(`${TEAM}/season`, "player")).toBe("season");
    // the training tips come from the analysis and sit under Saison, Teamleben on or off (K21)
    expect(destOf(`${TEAM}/season/tips`, "staff")).toBe("season");
    expect(sectionOf(`${TEAM}/season/tips`)).toBe("season");
    expect(destOf("/app/o/opponents/x", "staff")).toBeNull();
    expect(destOf("/app/o/drills", "staff")).toBe("team");
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
    expect(sectionOf("/app/o/feed")).toBe("myscenes");
    expect(sectionOf("/app/o/consents")).toBe("consents");
    expect(sectionOf("/app/o")).toBe("overview");
    expect(sectionOf("/app/o/settings")).toBeNull();
    expect(teamInPath(`${TEAM}/season`)).toBe(T);
    expect(teamInPath("/app/o")).toBeNull();
  });

  it("has at most one level of tabs with at most four items", () => {
    expect(sectionsFor("scenes", "staff", "o", T).map((i) => i.key)).toEqual(["scenes", "collections", "plays", "matrix"]);
    expect(sectionsFor("scenes", "player", "o", T).map((i) => i.key)).toEqual(["scenes", "collections", "plays", "matrix"]);
    expect(sectionsFor("scenes", "staff", "o", T)[1]?.href).toBe(`${TEAM}/collections`);
    // a single tab is no tab: the squad stays alone under Team, with or without Teamleben
    for (const d of ["matches", "season", "team"] as const)
      for (const m of MODES) {
        expect(sectionsFor(d, m, "o", T)).toEqual([]);
        expect(sectionsFor(d, m, "o", T, { teamFunctions: true })).toEqual([]);
      }
    for (const d of DESTS)
      for (const m of MODES)
        for (const on of [false, true]) expect(sectionsFor(d, m, "o", T, { teamFunctions: on }).length).toBeLessThanOrEqual(4);
  });

  it("bundles what Teamfunktionen switches on in one place, Teamleben (K16)", () => {
    const on = { teamFunctions: true };
    // off: no Teamleben for the team
    expect(navFor("staff", "o", T).some((i) => i.key === "life")).toBe(false);
    expect(navFor("player", "o", T).some((i) => i.key === "life")).toBe(false);
    expect(sectionsFor("life", "staff", "o", T)).toEqual([]);
    // on: a fifth destination, last
    expect(navFor("staff", "o", T, on).map((i) => i.key)).toEqual(["matches", "scenes", "season", "team", "life"]);
    expect(navFor("player", "o", T, on).map((i) => i.key)).toEqual(["matches", "scenes", "season", "team", "life"]);
    expect(navFor("staff", "o", T, on).at(-1)?.href).toBe("/app/o/schedule");
    expect(lifeHref("family", "o")).toBe("/app/o");
    // the staff plan and organise, players answer and see their own things, parents their child's
    expect(sectionsFor("life", "staff", "o", T, on).map((i) => i.key)).toEqual(["dates", "plan", "assignments"]);
    expect(sectionsFor("life", "staff", "o", T, on).map((i) => i.href)).toEqual(["/app/o/schedule", `${TEAM}/training`, `${TEAM}/assignments`]);
    expect(sectionsFor("life", "player", "o", T, on).map((i) => i.key)).toEqual(["dates", "assignments", "myscenes", "consents"]);
    expect(sectionsFor("life", "family", "o", T, on).map((i) => i.key)).toEqual(["overview", "dates", "consents"]);
    expect(sectionsFor("life", "family", "o", T).map((i) => i.key)).toEqual(["overview", "consents"]);
    // the routes stay reachable and keep their destination and tab
    for (const p of [`${TEAM}/training`, `${TEAM}/assignments`, "/app/o/schedule", "/app/o/assignments"])
      for (const m of MODES) expect(destOf(p, m)).toBe("life");
    expect(destOf("/app/o/feed/x", "player")).toBe("life");
    expect(destOf("/app/o/feed/x", "staff")).toBe("matches");
    expect(destOf("/app/o/consents", "family")).toBe("life");
    expect(destOf("/app/o/consents", "staff")).toBe("team");
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

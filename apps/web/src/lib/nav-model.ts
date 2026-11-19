/**
 * Navigation model (docs/design/ux-reset/SPEC.md, section 6; ADR 029): the team gets four
 * destinations, Spiele · Szenen · Saison · Team, the start is Spiele. Inside a destination there is
 * at most one level of tabs. Everything else is reached from inside them, the account menu or the
 * search.
 *
 * Players see everything of the team and work with the video like the staff (finding K18), so
 * they get the same four destinations. «Teamleben» (finding K16) is the one place for what the
 * team setting "Teamfunktionen" switches on: dates with RSVP, training, tasks and the areas of
 * players and parents. It is a fifth destination only while the setting is on; parents have only
 * it.
 */
import { worksWithVideo, coachRights } from "./roles";

export type Mode = "staff" | "player" | "family" | "guest";
export type Dest = "matches" | "scenes" | "season" | "team" | "life";

export interface NavItem {
  key: Dest;
  href: string;
}

export function modeFor(orgRole: string | null | undefined, teamRole: string | null | undefined): Mode {
  if (coachRights(orgRole, teamRole)) return "staff";
  if (teamRole === "player" || teamRole === "goalkeeper") return "player";
  if (teamRole === "parent") return "family";
  return "guest";
}

/** Who works with video (analysis tools, collections, uploads): Trainer, Co-Trainer and players. */
export function videoWork(orgRole: string | null | undefined, teamRole: string | null | undefined): boolean {
  return worksWithVideo(orgRole, teamRole);
}

/** Staff and players see the team's matches and scenes (K18). */
export function analyses(mode: Mode): boolean {
  return mode === "staff" || mode === "player";
}

/** Where a person lands in a club: Spiele for everyone in the team, Teamleben for parents. */
export function startHref(mode: Mode, orgId: string, teamId: string | null): string {
  const org = `/app/${orgId}`;
  if (mode !== "family" && teamId) return `${org}/teams/${teamId}/matches`;
  return org;
}

/** The one action reachable from everywhere: upload a match video. */
export function uploadHref(orgId: string, teamId: string | null): string | null {
  return teamId ? `/app/${orgId}/teams/${teamId}/matches?upload=1` : null;
}

/**
 * Team setting "Teamfunktionen" (ADR 029). Off: Teamleben (dates, RSVP, training, tasks, the
 * areas of players and parents) is out of the navigation and the search. Its routes stay.
 */
export interface NavOptions {
  teamFunctions?: boolean;
}

/** Where «Teamleben» opens for a mode: the dates for the team, the overview for parents. */
export function lifeHref(mode: Mode, orgId: string): string {
  return mode === "family" ? `/app/${orgId}` : `/app/${orgId}/schedule`;
}

export function navFor(mode: Mode, orgId: string, teamId: string | null, opts: NavOptions = {}): NavItem[] {
  const org = `/app/${orgId}`;
  const on = Boolean(opts.teamFunctions);
  const team: string | null = teamId ? `${org}/teams/${teamId}` : null;
  if (mode === "family") return [{ key: "life", href: lifeHref(mode, orgId) }];
  if (mode === "guest") return [{ key: "matches", href: team ? `${team}/matches` : org }, ...(team ? [{ key: "team" as const, href: team }] : [])];
  const items: (NavItem | null)[] = [
    { key: "matches", href: team ? `${team}/matches` : org },
    team ? { key: "scenes", href: `${team}/scenes` } : null,
    team ? { key: "season", href: `${team}/season` } : null,
    team ? { key: "team", href: team } : null,
    team && on ? { key: "life", href: lifeHref(mode, orgId) } : null,
  ];
  return items.filter((i): i is NavItem => Boolean(i));
}

export type Section =
  | "fixtures"
  | "season"
  | "scenes"
  | "collections"
  | "plays"
  | "matrix"
  | "plan"
  | "drills"
  | "assignments"
  | "roster"
  | "dates"
  | "overview"
  | "myscenes"
  | "consents";

const SECTION_OF_PAGE: Record<string, Section> = {
  // the club's root: the parents' overview (everyone else is sent on to Spiele)
  "": "overview",
  matches: "fixtures",
  paper: "fixtures",
  upload: "fixtures",
  // the official data and join requests change the squad
  official: "roster",
  "join-requests": "roster",
  // a player's season line is opened from the squad
  players: "roster",
  season: "season",
  // an opponent is part of the season
  opponents: "season",
  scenes: "scenes",
  search: "scenes",
  assistant: "scenes",
  library: "collections",
  collections: "collections",
  playlists: "collections",
  presentations: "collections",
  plays: "plays",
  matrix: "matrix",
  training: "plan",
  drills: "drills",
  assignments: "assignments",
  schedule: "dates",
  feed: "myscenes",
  consents: "consents",
};

function firstSegment(path: string): { first: string; inTeam: boolean } {
  const rest = path.replace(/^\/app\/[^/]+/, "") || "/";
  const inTeam = rest.startsWith("/teams/");
  const first = (inTeam ? rest.replace(/^\/teams\/[^/]+/, "") : rest).split("/")[1] ?? "";
  return { first, inTeam };
}

/** Which destination a path belongs to (pages below a destination keep it highlighted). */
export function destOf(path: string, mode: Mode): Dest | null {
  const rest = path.replace(/^\/app\/[^/]+/, "") || "/";
  const team = analyses(mode);
  const family = mode === "family";
  if (rest === "/") return family ? "life" : "matches";
  const { first, inTeam } = firstSegment(path);
  if (inTeam && first === "") return family ? "life" : "team";
  // Teamleben: dates, training, tasks, own scenes and consents of players and parents
  if (["schedule", "training", "assignments"].includes(first)) return "life";
  if (first === "feed") return mode === "staff" ? "matches" : "life";
  if (first === "consents") return mode === "staff" ? "team" : "life";
  if (family) return ["official", "join-requests", "players", "drills"].includes(first) ? null : "life";
  if (["matches", "paper", "upload"].includes(first)) return "matches";
  // an opponent is reached from a match, the season or a message: no tab claims it (UX-11)
  if (first === "opponents") return null;
  if (first === "season") return team ? "season" : "team";
  if (["scenes", "search", "assistant", "library", "collections", "playlists", "presentations", "plays", "matrix"].includes(first))
    return team ? "scenes" : "team";
  // drills are opened from «Dazu üben» (SPEC section 1, "Next"); they sit under Team
  if (first === "drills") return "team";
  if (["official", "join-requests", "players"].includes(first)) return "team";
  return null;
}

/** Active tab for a path. */
export function sectionOf(path: string): Section | null {
  const { first, inTeam } = firstSegment(path);
  if (inTeam && first === "") return "roster";
  return SECTION_OF_PAGE[first] ?? null;
}

/** Team id in a path, if any. */
export function teamInPath(path: string): string | null {
  return /\/teams\/([0-9a-f-]{36})/.exec(path)?.[1] ?? null;
}

export interface SubItem {
  key: Section;
  href: string;
}

/**
 * The one level of tabs inside a destination, never more than four. Szenen = search,
 * collections, plays, table. Spiele, Saison and Team have no tabs (a single tab is no tab).
 * Teamleben: for the staff dates, training plan and tasks; for players dates, tasks, own scenes
 * and consents; for parents the overview, the dates and the consents.
 */
export function sectionsFor(dest: Dest, mode: Mode, orgId: string, teamId: string | null, opts: NavOptions = {}): SubItem[] {
  const org = `/app/${orgId}`;
  const team = teamId ? `${org}/teams/${teamId}` : null;
  const on = Boolean(opts.teamFunctions);
  if (dest === "scenes" && analyses(mode) && team) {
    return [
      { key: "scenes", href: `${team}/scenes` },
      { key: "collections", href: `${team}/collections` },
      { key: "plays", href: `${team}/plays` },
      { key: "matrix", href: `${team}/matrix` },
    ];
  }
  if (dest !== "life") return [];
  if (mode === "staff" && team && on) {
    return [
      { key: "dates", href: `${org}/schedule` },
      // the training plan (SPEC section 1, "Next")
      { key: "plan", href: `${team}/training` },
      { key: "assignments", href: `${team}/assignments` },
    ];
  }
  if (mode === "player" && on) {
    return [
      { key: "dates", href: `${org}/schedule` },
      { key: "assignments", href: `${org}/assignments` },
      { key: "myscenes", href: `${org}/feed` },
      { key: "consents", href: `${org}/consents` },
    ];
  }
  if (mode === "family") {
    return [
      { key: "overview", href: org },
      ...(on ? [{ key: "dates" as const, href: `${org}/schedule` }] : []),
      { key: "consents", href: `${org}/consents` },
    ];
  }
  return [];
}

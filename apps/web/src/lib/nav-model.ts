/**
 * Navigation model (docs/design/ux-reset/SPEC.md, section 6; ADR 029): staff get four
 * destinations, Spiele · Szenen · Saison · Team, the start is Spiele. Inside a destination there is
 * at most one level of tabs. Everything else is reached from inside them, the account menu or the
 * search.
 */
export type Mode = "staff" | "player" | "family" | "guest";
export type Dest = "today" | "matches" | "scenes" | "season" | "team" | "dates";

export interface NavItem {
  key: Dest;
  href: string;
}

const STAFF_ROLES = new Set(["coach", "analyst", "team_manager", "goalkeeper_coach", "athletic_coach"]);

export function modeFor(orgRole: string | null | undefined, teamRole: string | null | undefined): Mode {
  if (orgRole === "org_admin" || STAFF_ROLES.has(teamRole ?? "")) return "staff";
  if (teamRole === "player" || teamRole === "goalkeeper") return "player";
  if (teamRole === "parent") return "family";
  return "guest";
}

/** Staff who work with video (analysis tools, collections, the data assistant). */
export function videoWork(orgRole: string | null | undefined, teamRole: string | null | undefined): boolean {
  return orgRole === "org_admin" || STAFF_ROLES.has(teamRole ?? "");
}

/** Where a person lands in a club: Spiele for staff (and guests), the start page for everyone else. */
export function startHref(mode: Mode, orgId: string, teamId: string | null): string {
  const org = `/app/${orgId}`;
  if ((mode === "staff" || mode === "guest") && teamId) return `${org}/teams/${teamId}/matches`;
  return org;
}

/** The one action reachable from everywhere for staff: upload a match video. */
export function uploadHref(orgId: string, teamId: string | null): string | null {
  return teamId ? `/app/${orgId}/teams/${teamId}/matches?upload=1` : null;
}

/**
 * Team setting "Teamfunktionen" (ADR 029). Off: training, dates, RSVP, tasks and the destinations
 * of players and parents are out of the navigation and the search. Their routes stay reachable.
 */
export interface NavOptions {
  teamFunctions?: boolean;
}

export function navFor(mode: Mode, orgId: string, teamId: string | null, opts: NavOptions = {}): NavItem[] {
  const org = `/app/${orgId}`;
  const on = Boolean(opts.teamFunctions);
  const team: string | null = teamId ? `${org}/teams/${teamId}` : null;
  const items: (NavItem | null)[] =
    mode === "staff"
      ? [
          { key: "matches", href: team ? `${team}/matches` : org },
          team ? { key: "scenes", href: `${team}/scenes` } : null,
          team ? { key: "season", href: `${team}/season` } : null,
          team ? { key: "team", href: team } : null,
        ]
      : mode === "player"
        ? [
            { key: "today", href: org },
            on ? { key: "scenes", href: `${org}/feed` } : null,
            on ? { key: "dates", href: `${org}/schedule` } : null,
            team ? { key: "team", href: team } : null,
          ]
        : mode === "family"
          ? [{ key: "today", href: org }, on ? { key: "dates", href: `${org}/schedule` } : null, team ? { key: "team", href: team } : null]
          : [{ key: "matches", href: team ? `${team}/matches` : org }, team ? { key: "team", href: team } : null];
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
  | "dates";

const SECTION_OF_PAGE: Record<string, Section> = {
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
  const staff = mode === "staff";
  const fan = mode === "player" || mode === "family";
  if (rest === "/") return fan ? "today" : "matches";
  const { first, inTeam } = firstSegment(path);
  if (inTeam && first === "") return "team";
  if (["matches", "paper", "upload"].includes(first)) return fan ? "scenes" : "matches";
  if (first === "feed") return staff ? "matches" : "scenes";
  if (["season", "opponents"].includes(first)) return staff ? "season" : "team";
  if (["scenes", "search", "assistant", "library", "collections", "playlists", "presentations", "plays", "matrix"].includes(first))
    return staff ? "scenes" : "team";
  // out of the navigation for staff (SPEC section 1, "Next"): the training plan, drills, tasks
  if (["training", "assignments", "drills"].includes(first)) return staff ? "team" : "today";
  if (first === "schedule") return staff ? "team" : "dates";
  if (["official", "join-requests", "players", "consents"].includes(first)) return "team";
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
 * The one level of tabs inside a destination, never more than four. Staff: Szenen = search,
 * collections, plays, table. Spiele and Saison have no tabs; Team has none either (a single tab is
 * no tab) unless "Teamfunktionen" is on: then squad, dates, training plan and tasks.
 * Players and parents: Team = squad and season.
 */
export function sectionsFor(dest: Dest, mode: Mode, orgId: string, teamId: string | null, opts: NavOptions = {}): SubItem[] {
  const org = `/app/${orgId}`;
  const team = teamId ? `${org}/teams/${teamId}` : null;
  const staff = mode === "staff";
  if (dest === "scenes" && staff && team) {
    return [
      { key: "scenes", href: `${team}/scenes` },
      { key: "collections", href: `${team}/library` },
      { key: "plays", href: `${team}/plays` },
      { key: "matrix", href: `${team}/matrix` },
    ];
  }
  if (dest === "team" && team && staff && opts.teamFunctions) {
    return [
      { key: "roster", href: team },
      { key: "dates", href: `${org}/schedule` },
      { key: "plan", href: `${team}/training` },
      { key: "assignments", href: `${team}/assignments` },
    ];
  }
  if (dest === "team" && team && !staff) {
    return [
      { key: "roster", href: team },
      { key: "season", href: `${team}/season` },
    ];
  }
  return [];
}

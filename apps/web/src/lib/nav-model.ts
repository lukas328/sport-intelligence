/**
 * Navigation model (docs/DESIGN.md, "Navigation"): at most four destinations per role, everything
 * else is reached from inside them, the account menu or the command palette.
 */
export type Mode = "staff" | "player" | "family" | "guest";
export type Dest = "today" | "matches" | "team" | "training" | "scenes" | "dates";

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

/** Staff who work with video (analysis tools, assignments, the data assistant). */
export function videoWork(orgRole: string | null | undefined, teamRole: string | null | undefined): boolean {
  return orgRole === "org_admin" || STAFF_ROLES.has(teamRole ?? "");
}

export function navFor(mode: Mode, orgId: string, teamId: string | null): NavItem[] {
  const org = `/app/${orgId}`;
  const team: string | null = teamId ? `${org}/teams/${teamId}` : null;
  // staff order follows the coach's week: the match, its analysis, the training, then the squad
  const items: (NavItem | null)[] =
    mode === "staff"
      ? [
          { key: "today", href: org },
          team ? { key: "matches", href: `${team}/matches` } : null,
          team ? { key: "training", href: `${team}/training` } : null,
          team ? { key: "team", href: team } : null,
        ]
      : mode === "player"
        ? [
            { key: "today", href: org },
            { key: "scenes", href: `${org}/feed` },
            { key: "dates", href: `${org}/schedule` },
            team ? { key: "team", href: team } : null,
          ]
        : mode === "family"
          ? [{ key: "today", href: org }, { key: "dates", href: `${org}/schedule` }, team ? { key: "team", href: team } : null]
          : [{ key: "today", href: org }, team ? { key: "matches", href: `${team}/matches` } : null, team ? { key: "team", href: team } : null];
  return items.filter((i): i is NavItem => Boolean(i));
}

export type Section = "fixtures" | "season" | "library" | "plan" | "drills" | "plays" | "assignments" | "roster" | "dates";

const SECTION_OF_PAGE: Record<string, Section> = {
  matches: "fixtures",
  paper: "fixtures",
  // an opponent is opened from a fixture
  opponents: "fixtures",
  // the official data and join requests change the squad
  official: "roster",
  "join-requests": "roster",
  season: "season",
  matrix: "season",
  assistant: "season",
  library: "library",
  playlists: "library",
  presentations: "library",
  search: "library",
  training: "plan",
  drills: "drills",
  plays: "plays",
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
  if (rest === "/") return "today";
  const { first, inTeam } = firstSegment(path);
  if (inTeam && first === "") return "team";
  const staff = mode === "staff";
  const fan = mode === "player" || mode === "family";
  if (["matches", "opponents", "paper"].includes(first)) return fan ? "scenes" : "matches";
  if (first === "feed") return staff ? "matches" : "scenes";
  if (["training", "assignments", "drills"].includes(first)) return staff ? "training" : "today";
  if (first === "plays") return staff ? "training" : "team";
  if (first === "schedule") return staff ? "team" : "dates";
  if (["official", "join-requests"].includes(first)) return "team";
  if (["season", "matrix", "assistant", "library", "playlists", "presentations", "search"].includes(first)) return staff ? "matches" : "team";
  return null;
}

/** Active second-level item for a path. */
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
 * Second level of a destination (sidebar on desktop, links under the title on phones), never more
 * than four. Staff: Spiele = fixtures, season, library; Training = plan, drills, plays,
 * assignments; Team = squad and dates. Everyone else: Team = squad and season.
 */
export function sectionsFor(dest: Dest, mode: Mode, orgId: string, teamId: string | null): SubItem[] {
  const org = `/app/${orgId}`;
  const team = teamId ? `${org}/teams/${teamId}` : null;
  const staff = mode === "staff";
  if (dest === "matches" && staff && team) {
    return [
      { key: "fixtures", href: `${team}/matches` },
      { key: "season", href: `${team}/season` },
      { key: "library", href: `${team}/library` },
    ];
  }
  if (dest === "training" && staff) {
    return [
      ...(team ? [{ key: "plan" as const, href: `${team}/training` }] : []),
      { key: "drills", href: `${org}/drills` },
      ...(team ? [{ key: "plays" as const, href: `${team}/plays` }] : []),
      ...(team ? [{ key: "assignments" as const, href: `${team}/assignments` }] : []),
    ];
  }
  if (dest === "team" && team) {
    return staff
      ? [
          { key: "roster", href: team },
          { key: "dates", href: `${org}/schedule` },
        ]
      : [
          { key: "roster", href: team },
          { key: "season", href: `${team}/season` },
        ];
  }
  return [];
}

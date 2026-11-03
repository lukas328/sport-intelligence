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
  const items: (NavItem | null)[] =
    mode === "staff"
      ? [
          { key: "today", href: org },
          team ? { key: "matches", href: `${team}/matches` } : null,
          team ? { key: "team", href: team } : null,
          team ? { key: "training", href: `${team}/training` } : null,
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

/** Which destination a path belongs to (pages below a destination keep it highlighted). */
export function destOf(path: string, mode: Mode): Dest | null {
  const rest = path.replace(/^\/app\/[^/]+/, "") || "/";
  if (rest === "/") return "today";
  const sub = rest.replace(/^\/teams\/[^/]+/, "");
  const inTeam = rest.startsWith("/teams/");
  const first = (inTeam ? sub : rest).split("/")[1] ?? "";
  if (inTeam && first === "") return "team";
  if (["matches", "opponents", "paper"].includes(first)) return mode === "player" || mode === "family" ? "scenes" : "matches";
  if (["training", "assignments", "drills"].includes(first)) return mode === "staff" ? "training" : "today";
  if (first === "schedule") return mode === "staff" ? "training" : "dates";
  if (first === "feed") return mode === "staff" ? "matches" : "scenes";
  if (["season", "matrix", "library", "playlists", "plays", "presentations", "search", "assistant"].includes(first)) return "team";
  return null;
}

export type TeamSection = "roster" | "season" | "library";
export type TrainingSection = "plan" | "dates" | "drills" | "assignments";

export function teamSectionOf(path: string): TeamSection | null {
  const first = path.replace(/^\/app\/[^/]+(\/teams\/[^/]+)?/, "").split("/")[1] ?? "";
  if (first === "") return "roster";
  if (["season", "matrix", "assistant"].includes(first)) return "season";
  if (["library", "playlists", "plays", "presentations", "search"].includes(first)) return "library";
  return null;
}

export function trainingSectionOf(path: string): TrainingSection | null {
  const first = path.replace(/^\/app\/[^/]+(\/teams\/[^/]+)?/, "").split("/")[1] ?? "";
  return ({ training: "plan", schedule: "dates", drills: "drills", assignments: "assignments" } as const)[first as "training"] ?? null;
}

/** Team id in a path, if any. */
export function teamInPath(path: string): string | null {
  return /\/teams\/([0-9a-f-]{36})/.exec(path)?.[1] ?? null;
}

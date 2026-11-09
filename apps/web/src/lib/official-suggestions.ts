import type { Schemas } from "@handball/api-client";

/** What the official data proposes for a team: squad changes, reports to import, schedule
 * changes, a new season. The coach accepts or dismisses each; nothing changes on its own. */
export type Suggestion = Schemas["SuggestionOut"];
export type SuggestionKind = Suggestion["kind"];

export interface RosterStats {
  games: number | null;
  goals: number | null;
  goals_7m: number | null;
  attempts_7m: number | null;
  suspensions_2min: number | null;
  goalkeeper: boolean | null;
  saves: number | null;
  shots_faced: number | null;
}

export interface Groups {
  roster: Suggestion[];
  reports: Suggestion[];
  schedule: Suggestion[];
  seasons: Suggestion[];
}

const str = (v: unknown) => (typeof v === "string" ? v : "");
const num = (v: unknown) => (typeof v === "number" ? v : null);

/** The open suggestions in the order a coach works through them: the squad (most appearances
 * first, then by name), reports and schedule by date, new seasons. */
export function groupSuggestions(list: Suggestion[]): Groups {
  const open = list.filter((s) => s.status === "open");
  const rosterRank = (k: SuggestionKind) => (k === "roster_add" ? 0 : k === "roster_number" ? 1 : 2);
  const byDate = (a: Suggestion, b: Suggestion) => str(a.payload.kickoff_at).localeCompare(str(b.payload.kickoff_at));
  return {
    roster: open
      .filter((s) => s.kind.startsWith("roster_"))
      .sort(
        (a, b) =>
          rosterRank(a.kind) - rosterRank(b.kind) ||
          (num(b.payload.appearances) ?? 0) - (num(a.payload.appearances) ?? 0) ||
          str(a.payload.last_name).localeCompare(str(b.payload.last_name), "de-CH"),
      ),
    reports: open.filter((s) => s.kind === "report").sort(byDate),
    schedule: open.filter((s) => s.kind === "match_new" || s.kind === "match_moved").sort(byDate),
    seasons: open.filter((s) => s.kind === "season_new"),
  };
}

/** The statistics of a roster suggestion, null when the player has no game yet. */
export const rosterStats = (s: Suggestion): RosterStats | null => (s.payload.stats as RosterStats | null | undefined) ?? null;

/** "3/5" for 7 m goals of attempts, "-" when unknown. */
export const sevenM = (st: RosterStats | null) => (st?.goals_7m == null ? "-" : st.attempts_7m == null ? String(st.goals_7m) : `${st.goals_7m}/${st.attempts_7m}`);

/** The shirt number typed for a new player: empty is none, else 0 to 99. Undefined when invalid. */
export function parseNumber(text: string): number | null | undefined {
  const t = text.trim();
  if (!t) return null;
  if (!/^\d{1,2}$/.test(t)) return undefined;
  return Number(t);
}

/** Shirt numbers given to more than one of the chosen players (the official data repeats numbers
 * across games); the API would leave the second one empty, so the coach fixes it first. */
export function duplicateNumbers(numbers: (number | null | undefined)[]): Set<number> {
  const seen = new Set<number>();
  const twice = new Set<number>();
  for (const n of numbers) if (n != null) (seen.has(n) ? twice : seen).add(n);
  return twice;
}

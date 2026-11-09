import type { Schemas } from "@handball/api-client";

/** Teams from the official data (handball.ch) the coach can take over, ask to join or open. */
export type OfficialTeam = Schemas["OfficialTeamHit"];

export interface ClubGroup {
  id: number;
  name: string;
  city: string | null;
  teams: OfficialTeam[];
}

/** Hits grouped by club, clubs in the order of their first hit; within a club the teams already in
 * the app first (open or ask), otherwise the search's own order (the club's first team on top). */
export function groupByClub(hits: OfficialTeam[]): ClubGroup[] {
  const groups = new Map<number, ClubGroup>();
  for (const h of hits) {
    const g = groups.get(h.club.id) ?? { id: h.club.id, name: h.club.name, city: h.club.city, teams: [] };
    g.teams.push(h);
    groups.set(h.club.id, g);
  }
  const rank = (s: OfficialTeam["status"]) => (s === "member" ? 0 : s === "claimed" ? 1 : 2);
  for (const g of groups.values()) g.teams.sort((a, b) => rank(a.status) - rank(b.status));
  return [...groups.values()];
}

/** The search needs three letters (the API answers 422 below). */
export const searchable = (q: string) => q.trim().length >= 3;

/** A club with many teams shows this many until the coach asks for all. */
export const FOLD_AT = 8;

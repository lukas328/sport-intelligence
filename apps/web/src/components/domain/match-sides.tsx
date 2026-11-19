"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { createContext, useContext, type ReactNode } from "react";
import { api } from "@/lib/client";
import { perspectiveOf, sideLabel, type MatchSides } from "@/lib/match-sides";

/**
 * The sides of the match on screen for every part of a match page (lib/match-sides.ts): set once
 * by the page, read by the parts that name a team. Without a provider (start, season, demos) the
 * parts speak from the team's point of view as before.
 */
const SidesContext = createContext<MatchSides | null>(null);

export function MatchSidesProvider({ sides, children }: { sides: MatchSides; children: ReactNode }) {
  return <SidesContext.Provider value={sides}>{children}</SidesContext.Provider>;
}

export function useMatchSides(): MatchSides | null {
  return useContext(SidesContext);
}

/** «Wir» for our side in a match of the team, the team's name in an observed match. */
export function useSideLabel(): (side: "own" | "opp" | "opponent", oppName?: string) => string {
  const t = useTranslations("anlauf");
  const sides = useContext(SidesContext);
  return (side, oppName) => {
    if (!sides) return side === "own" ? t("us") : (oppName ?? "");
    return sideLabel(sides, side, t("us"));
  };
}

type RosterRow = Schemas["RosterEntryOut"];
type Rostered = { kind?: string | null; team_id: string; season_id: string };

/**
 * The team's roster for a match's player pickers. An observed match has none of our players (L4):
 * the account team never appears there; both playing teams are picked by shirt number.
 */
export function useMatchRoster(orgId: string, match: Rostered): { data: RosterRow[] | undefined; isSuccess: boolean; isLoading: boolean } {
  const neutral = perspectiveOf(match) === "neutral";
  // the key of the other roster readers (useRosterNames); an observed match does not ask
  const q = useQuery({
    enabled: !neutral && Boolean(match.season_id),
    queryKey: ["roster", match.season_id],
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster", { params: { path: { org_id: orgId, team_id: match.team_id, season_id: match.season_id } } })).data ?? [],
  });
  if (neutral) return { data: [], isSuccess: true, isLoading: false };
  return { data: q.data, isSuccess: q.isSuccess, isLoading: q.isLoading };
}

/** The observed opponent's known squad: shirt numbers with names, where the club recorded them. */
export function useOpponentSquad(orgId: string, opponentId: string | null | undefined) {
  return useQuery({
    queryKey: ["opponent-players", opponentId],
    enabled: Boolean(opponentId),
    staleTime: 300_000,
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/opponents/{opponent_id}/players", { params: { path: { org_id: orgId, opponent_id: opponentId! } } })).data ?? [],
  });
}

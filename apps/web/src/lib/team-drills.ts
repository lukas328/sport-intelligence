"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/client";
import type { DrillItem } from "@/lib/drill-snapshot";

export type TeamDrill = Schemas["DrillOut"];

/** The team's one drill list: its own drills, the ones shared in the club, then the library. */
export function useTeamDrills(orgId: string, teamId: string | null | undefined, lang: string) {
  return useQuery({
    queryKey: ["team-drills", teamId, lang],
    enabled: !!teamId,
    queryFn: async () =>
      (
        await api.GET("/v1/orgs/{org_id}/teams/{team_id}/drills", {
          params: { path: { org_id: orgId, team_id: teamId! }, query: { lang: (["de-CH", "en", "fr"].includes(lang) ? lang : "de-CH") as "de-CH" } },
        })
      ).data ?? [],
  });
}

/** A drill of the list as stored in a session (a snapshot: later edits keep the plan). */
export function drillItemOf(d: TeamDrill): DrillItem {
  return { drill_id: d.id, name: d.name, minutes: d.minutes, focus: [...d.focus], setup: d.setup, coaching: d.coaching };
}

"use client";

import { useQuery } from "@tanstack/react-query";
import { Check, Minus, X } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";

/**
 * Before filming: per player and purpose whether the consent is given, refused or missing, with
 * the count per purpose ("12 von 14"). Coaches, team managers and club admins only (others get
 * 403 and see nothing here).
 */
export function ConsentOverview({ orgId, teamId, seasonId }: { orgId: string; teamId: string; seasonId: string }) {
  const t = useTranslations("consents");
  const format = useFormatter();
  const q = useQuery({
    queryKey: ["consent-overview", teamId, seasonId],
    retry: false,
    queryFn: async () => {
      const r = await api.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/consents", {
        params: { path: { org_id: orgId, team_id: teamId, season_id: seasonId } },
      });
      if (r.error) throw r.error;
      return r.data;
    },
  });
  const data = q.data;
  if (!data || data.players.length === 0) return null;
  const purposes = data.summary.filter((s) => s.applicable);
  const Mark = { granted: Check, refused: X, missing: Minus } as const;
  return (
    <details className="group text-sm" data-testid="consent-overview">
      <summary className="cursor-pointer font-medium underline decoration-foreground/35 decoration-dotted underline-offset-4 hover:decoration-solid">{t("overviewOpen")}</summary>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[34rem] text-sm">
          <caption className="sr-only">{t("overviewTitle")}</caption>
          <thead>
            <tr className="border-b-2 border-foreground">
              <th scope="col" className="py-1.5 text-left font-medium">
                <span className="sr-only">{t("player")}</span>
              </th>
              {purposes.map((s) => (
                <th key={s.kind} scope="col" className="px-2 py-1.5 text-left align-bottom font-medium">
                  <span className="block">{t(`purpose_${s.kind}` as "purpose_analysis")}</span>
                  <span className="block font-score text-xs font-normal text-muted tabular-nums">{t("countOf", { n: s.granted, total: s.players })}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.players.map((p) => (
              <tr key={p.player_id} className="border-b border-foreground/10">
                <th scope="row" className="py-1.5 pr-2 text-left font-medium whitespace-nowrap">
                  {p.jersey_number != null && <span className="mr-1.5 font-score text-muted tabular-nums">{p.jersey_number}</span>}
                  {p.first_name} {p.last_name}
                </th>
                {purposes.map((s) => {
                  const c = p.purposes.find((x) => x.kind === s.kind);
                  const state = c?.state ?? "missing";
                  const Icon = Mark[state];
                  const since = c?.since ? format.dateTime(new Date(c.since), { day: "numeric", month: "short" }) : null;
                  return (
                    <td key={s.kind} className={cn("px-2 py-1.5", state === "granted" ? "text-foreground" : "text-muted")}>
                      <Icon aria-hidden className="mr-1 inline size-3.5" strokeWidth={state === "granted" ? 3 : 2} />
                      <span className={cn(state === "granted" && "sr-only")}>{t(`state_${state}`)}</span>
                      {state === "granted" && since && <span className="sr-only">{` ${since}`}</span>}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { BackLink } from "@/components/ui/back-link";
import { EmptyState } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { useShell } from "@/components/shell/context";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";

type Line = Schemas["SeasonLine"];
type Figures = Schemas["LineFigures"];

const pct = (v: number | null | undefined) => (v == null ? "-" : `${Math.round(v * 100)} %`);

/**
 * A player's season as a line of the match sheet: per played match the figures, every figure
 * leading to its scenes (staff: the scene search for that player and match). Totals on top.
 */
export function SeasonLineView({ orgId, teamId, playerId }: { orgId: string; teamId: string; playerId: string }) {
  const t = useTranslations("seasonLine");
  const format = useFormatter();
  const { mode } = useShell();
  const staff = mode === "staff";
  const team = { org_id: orgId, team_id: teamId };
  const line = useQuery({
    queryKey: ["season-line", teamId, playerId],
    retry: false,
    queryFn: async () => {
      const info = (await api.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: team } })).data;
      if (!info?.current_season) return null;
      const r = await api.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/players/{player_id}/line", {
        params: { path: { ...team, season_id: info.current_season.id, player_id: playerId } },
      });
      if (r.error) throw r.error;
      return r.data as Line;
    },
  });
  const l = line.data;
  const back = <BackLink fallback={`/app/${orgId}/teams/${teamId}`} />;
  if (line.isPending) return back;
  if (!l) return (
    <div className="space-y-4">
      {back}
      <EmptyState title={t("notFound")} />
    </div>
  );
  const keeper = l.main_position === "TW";
  // the figures of one line, in match-sheet order; each one with the search filter behind it
  const cols: { key: string; label: string; value: (f: Figures, m?: Schemas["SeasonLineMatch"]) => string; filter?: string }[] = keeper
    ? [
        { key: "saves", label: t("saves"), value: (f) => String(f.saves), filter: "type=shot&outcome=save" },
        { key: "faced", label: t("faced"), value: (f) => String(f.faced) },
        { key: "save_pct", label: t("savePct"), value: (_f, m) => pct(m ? m.save_pct : l.totals.save_pct) },
        { key: "seven", label: t("sevenM"), value: (f) => `${f.seven_m_saves}/${f.seven_m_faced}` },
      ]
    : [
        { key: "goals", label: t("goals"), value: (f) => String(f.goals), filter: "type=shot&outcome=goal" },
        { key: "shots", label: t("shots"), value: (f) => String(f.goals + f.saved + f.misses + f.posts + f.blocked), filter: "type=shot" },
        { key: "pct", label: t("shootingPct"), value: (_f, m) => pct(m ? m.shooting_pct : l.totals.shooting_pct) },
        { key: "seven", label: t("sevenM"), value: (f) => `${f.seven_m_goals}/${f.seven_m_shots}` },
        { key: "assists", label: t("assists"), value: (f) => String(f.assists) },
        { key: "turnovers", label: t("turnovers"), value: (f) => String(f.turnovers), filter: "type=turnover" },
        { key: "suspensions", label: t("suspensions"), value: (f) => String(f.suspensions), filter: "type=suspension_2min" },
      ];
  const search = (filter: string, matchId?: string) => `/app/${orgId}/teams/${teamId}/search?player=${playerId}${matchId ? `&match=${matchId}` : ""}&${filter}`;
  const cell = (c: (typeof cols)[number], f: Figures, m?: Schemas["SeasonLineMatch"]) => {
    const v = c.value(f, m);
    // a count leads to its scenes; zeros and rates do not
    return staff && c.filter && v !== "0" ? (
      <Link href={search(c.filter, m?.match_id)} className="underline decoration-foreground/35 decoration-dotted underline-offset-4 hover:decoration-solid">
        {v}
      </Link>
    ) : (
      v
    );
  };
  const tot = l.totals as unknown as Figures;
  return (
    <div className="space-y-8">
      <div>
        {back}
        <PageHeader
          eyebrow={t("title")}
          title={`${l.jersey_number != null ? `#${l.jersey_number} ` : ""}${l.first_name} ${l.last_name}`}
          description={t("summary", { matches: l.totals.matches, involved: l.totals.matches_involved, present: l.totals.matches_present })}
        />
      </div>
      {/* the season in one printed row, every count leads to its scenes */}
      <dl className="grid grid-cols-3 gap-x-6 gap-y-4 border-y-2 border-foreground py-4 sm:grid-cols-4 lg:grid-cols-7" data-testid="season-line-totals">
        {cols.map((c) => (
          <div key={c.key}>
            <dt className="text-[0.8125rem] text-muted">{c.label}</dt>
            <dd className="mt-1 font-score text-[1.75rem] leading-none tabular-nums">{cell(c, tot)}</dd>
          </div>
        ))}
      </dl>
      {l.matches.length === 0 ? (
        <p className="text-[0.9375rem] text-muted">{t("noMatches")}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[36rem] text-sm" data-testid="season-line-matches">
            <caption className="sr-only">{t("matches")}</caption>
            <thead>
              <tr className="border-b-2 border-foreground text-left">
                <th scope="col" className="py-1.5 font-medium">{t("match")}</th>
                <th scope="col" className="px-2 py-1.5 font-medium">{t("result")}</th>
                {cols.map((c) => (
                  <th key={c.key} scope="col" className="px-2 py-1.5 text-right font-medium">{c.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {l.matches.map((m) => (
                <tr key={m.match_id} className={cn("border-b border-foreground/10", !m.involved && "text-muted")}>
                  <th scope="row" className="py-2 pr-2 text-left font-medium">
                    <Link href={`/app/${orgId}/matches/${m.match_id}`} className="hover:underline hover:underline-offset-4">
                      <span className="text-muted tabular-nums">{format.dateTime(new Date(m.kickoff_at), { day: "numeric", month: "numeric" })}</span>{" "}
                      {t(m.is_home ? "home" : "away", { opponent: m.opponent })}
                    </Link>
                  </th>
                  <td className="px-2 py-2 font-score tabular-nums">
                    {m.score_own != null ? `${m.score_own}:${m.score_opponent}` : "-"}
                  </td>
                  {cols.map((c) => (
                    <td key={c.key} className="px-2 py-2 text-right font-score tabular-nums">
                      {m.involved ? cell(c, m.figures, m) : "-"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-xs text-muted">{t("source")}</p>
    </div>
  );
}

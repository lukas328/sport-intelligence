"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { useInsightText, type Insight } from "@/components/analysis/insights";
import { api } from "@/lib/client";

interface ThemeMatch {
  match_id: string;
  fired: boolean;
  value: number | null;
  scenes: { event_id: string; t_ms: number | null }[];
}
interface Theme {
  id: string;
  kind: "strength" | "weakness";
  key: string;
  params: Record<string, string | number | null>;
  matches: number;
  of: number;
  per_match: ThemeMatch[];
}
interface ThemesData {
  matches_with_video: number;
  matches: { match_id: string; kickoff_at: string }[];
  themes: Theme[];
}

/** A theme's figure as text: shares in percent, counts as they are; no value stays empty. */
function figure(v: number | null): string {
  if (v == null) return "";
  return v <= 1 && !Number.isInteger(v) ? `${Math.round(v * 100)} %` : String(v);
}

/**
 * "Was sich wiederholt" (SPEC 7.9): themes from at least two matches with video, each with its
 * sentence, from how many matches it comes, one value per match and the scenes behind it. Plain
 * list until the new look; nothing is shown below two matches with video.
 */
export function SeasonThemes({ orgId, teamId, seasonId, names }: { orgId: string; teamId: string; seasonId: string; names: Record<string, string> }) {
  const t = useTranslations("themes");
  const tp = useTranslations("positions");
  const format = useFormatter();
  const text = useInsightText(names);
  const q = useQuery({
    queryKey: ["themes", teamId, seasonId],
    queryFn: async () =>
      ((
        await api.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/themes", {
          params: { path: { org_id: orgId, team_id: teamId, season_id: seasonId } },
        })
      ).data ?? null) as ThemesData | null,
  });
  const data = q.data;
  if (!data || data.themes.length === 0) return null;
  const when = Object.fromEntries(data.matches.map((m) => [m.match_id, format.dateTime(new Date(m.kickoff_at), { day: "numeric", month: "numeric" })]));
  const sentence = (th: Theme) =>
    th.key === "themes.conceded_position"
      ? t("conceded_position", { position: tp(String(th.params.position) as "LA"), k: th.params.k ?? 0, n: th.params.n ?? 0 })
      : text({ ...th, score: 0, sample: 0, evidence: {} } as Insight);
  return (
    <section aria-labelledby="themes-title" className="space-y-4" data-testid="season-themes">
      <h2 id="themes-title" className="text-2xl">
        {t("title")}
      </h2>
      <ol className="space-y-6">
        {data.themes.map((th) => (
          <li key={th.id} className="space-y-2 border-t border-foreground/15 pt-3">
            <p className="font-semibold">{sentence(th)}</p>
            <p className="text-sm text-muted">{t("fromMatches", { k: th.matches, n: th.of })}</p>
            <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
              {th.per_match.map((p) => {
                const first = p.scenes[0];
                const label = `${when[p.match_id] ?? ""} ${figure(p.value)}`.trim();
                return (
                  <li key={p.match_id} className={p.fired ? "font-semibold" : "text-muted"}>
                    {first ? (
                      <Link href={`/app/${orgId}/matches/${p.match_id}?tab=video${first.t_ms != null ? `&t=${first.t_ms}` : ""}`} className="underline underline-offset-4">
                        {label} · {t("scenes", { n: p.scenes.length })}
                      </Link>
                    ) : (
                      label
                    )}
                  </li>
                );
              })}
            </ul>
          </li>
        ))}
      </ol>
    </section>
  );
}

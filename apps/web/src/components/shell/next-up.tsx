"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useFormatter, useNow, useTranslations } from "next-intl";
import { api } from "@/lib/client";
import { useShell } from "./context";

/** The next match of the active team, always one click away in the sidebar. */
export function NextUp() {
  const t = useTranslations();
  const format = useFormatter();
  const now = useNow({ updateInterval: 60_000 });
  const { org, team } = useShell();
  const q = useQuery({
    queryKey: ["team-matches", team?.id],
    enabled: Boolean(team),
    staleTime: 60_000,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/matches", { params: { path: { org_id: org.id, team_id: team!.id } } })).data ?? [],
  });
  const next = (q.data ?? [])
    .filter((m) => new Date(m.kickoff_at).getTime() > now.getTime() - 3 * 3600_000 && m.score_own == null && !m.has_video)
    .sort((a, b) => a.kickoff_at.localeCompare(b.kickoff_at))[0];
  if (!next) return null;
  const when = new Date(next.kickoff_at);
  return (
    <Link href={`/app/${org.id}/matches/${next.id}`} className="block px-3 py-2.5 border border-border transition-colors hover:bg-surface">
      <span className="block text-xs font-medium text-muted">{t("today.next")}</span>
      <span className="mt-0.5 block truncate text-sm font-semibold">{next.kind === "training" ? t("matches.training") : next.opponent_name}</span>
      <span className="block text-xs text-muted tabular-nums">
        {format.dateTime(when, { weekday: "short", day: "numeric", month: "short" })} · {format.dateTime(when, { hour: "2-digit", minute: "2-digit" })}
      </span>
    </Link>
  );
}

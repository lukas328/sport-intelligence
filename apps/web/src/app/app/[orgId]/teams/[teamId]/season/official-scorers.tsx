"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { SectionHead } from "@/components/anlauf/blocks";
import { api } from "@/lib/client";

/**
 * «Wer trifft» of the season: one count with the start (third real-video test G6). With the
 * team linked to handball.ch the scorers come from the same player statistics of the played
 * games as on Spiele; without the link, or while handball.ch does not answer, the goals from
 * the app's own events (`fallback`).
 */
export function OfficialScorers({ club, team, fallback }: { club: number | null; team: number | null; fallback: ReactNode }) {
  const t = useTranslations("entry");
  const q = useQuery({
    queryKey: ["public-team-scorers", club, team],
    enabled: club != null && team != null,
    retry: false,
    staleTime: 600_000,
    queryFn: async () => (await api.GET("/v1/public/clubs/{club_id}/teams/{official_id}", { params: { path: { club_id: club!, official_id: team! }, query: { scorers: true } } })).data ?? null,
  });
  const p = q.data;
  if (club == null || team == null || q.isError || (q.isSuccess && (!p || p.scorers.length === 0))) return <>{fallback}</>;
  if (!p) return <p className="m-0 text-[15px] text-ink-2" aria-live="polite">{t("scorersLoading")}</p>;
  return (
    <section data-testid="season-scorers-official">
      <SectionHead title={t("scorers")} note={t("scorersBasis", { n: p.scorer_games })} />
      <ol className="m-0 list-none p-0">
        {p.scorers.map((s) => (
          <li key={s.name} className="flex justify-between border-b border-rule py-2 text-[17px]">
            <span>{s.name}</span>
            <b className="tabular-nums">{s.goals}</b>
          </li>
        ))}
      </ol>
    </section>
  );
}

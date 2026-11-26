"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { linkClass } from "@/components/anlauf/blocks";
import { api } from "@/lib/client";
import { numberGaps } from "@/lib/roster-numbers";
import { cn } from "@/lib/utils";

/**
 * Before the analysis names people (the upload, the people step): a squad with shirt numbers is
 * what lets it name them by the number it reads (audit #160). Says who has no number and which
 * number two players share, or that there is no squad yet, with the way to complete it; nothing
 * when the squad is complete.
 */
export function RosterNumberHint({ orgId, teamId, seasonId, className }: { orgId: string; teamId: string; seasonId: string; className?: string }) {
  const t = useTranslations("roster");
  const q = useQuery({
    queryKey: ["roster", seasonId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster", { params: { path: { org_id: orgId, team_id: teamId, season_id: seasonId } } })).data ?? [],
  });
  if (!q.data) return null;
  const active = q.data.filter((e) => e.active !== false);
  const { without, duplicates } = numberGaps(active);
  if (active.length > 0 && !without.length && !duplicates.length) return null;
  const name = (e: { first_name: string; last_name: string }) => `${e.first_name} ${e.last_name}`;
  return (
    <div className={cn("max-w-[62ch] border-l-4 border-attn pl-3", className)} role="status" data-testid="roster-number-hint">
      {active.length === 0 ? (
        <p className="m-0 text-[15px]">{t("hintNoSquad")}</p>
      ) : (
        <>
          {without.length > 0 && (
            <p className="m-0 text-[15px]" data-testid="roster-without-number">
              <span className="font-semibold">{t("hintWithout", { n: without.length })}</span> {without.slice(0, 6).map(name).join(", ")}
              {without.length > 6 ? ` ${t("hintMore", { n: without.length - 6 })}` : ""}
            </p>
          )}
          {duplicates.map(([n, list]) => (
            <p key={n} className="m-0 mt-1 text-[15px]" data-testid="roster-duplicate-number">
              <span className="font-semibold">{t("hintTwice", { n })}</span> {list.map(name).join(", ")}
            </p>
          ))}
        </>
      )}
      <Link href={`/app/${orgId}/teams/${teamId}?edit=1`} className={cn(linkClass, "mt-1 inline-flex min-h-11 items-center")} data-testid="roster-number-link">
        {t(active.length === 0 ? "hintAddSquad" : "hintComplete")}
      </Link>
    </div>
  );
}

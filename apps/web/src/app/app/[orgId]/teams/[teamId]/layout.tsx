import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { TabLink } from "@/components/tab-link";
import { serverApi } from "@/lib/api";

export default async function TeamLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ orgId: string; teamId: string }>;
}) {
  const { orgId, teamId } = await params;
  const t = await getTranslations();
  const { data: team } = await (await serverApi()).GET("/v1/orgs/{org_id}/teams/{team_id}", {
    params: { path: { org_id: orgId, team_id: teamId } },
  });
  if (!team) notFound();
  const base = `/app/${orgId}/teams/${teamId}`;
  return (
    <div className="space-y-6">
      <header className="space-y-3">
        <div>
          <h1 className="text-2xl font-semibold">{team.name}</h1>
          {team.current_season && (
            <p className="text-sm text-muted">{t("roster.season", { label: team.current_season.label })}</p>
          )}
        </div>
        <nav aria-label={team.name} className="flex gap-1 border-b border-border">
          <TabLink href={`${base}/matches`}>{t("team.matches")}</TabLink>
          <TabLink href={base} exact>
            {t("team.roster")}
          </TabLink>
          <TabLink href={`${base}/playlists`}>{t("team.playlists")}</TabLink>
          <TabLink href={`${base}/plays`}>{t("team.plays")}</TabLink>
        </nav>
      </header>
      {children}
    </div>
  );
}

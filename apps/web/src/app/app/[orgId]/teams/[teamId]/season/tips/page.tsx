import type { Metadata } from "next";
import Link from "next/link";
import { Replace } from "@/components/shell/replace";
import { ChevronLeft } from "lucide-react";
import { getTranslations } from "next-intl/server";
import { PageHeader } from "@/components/ui/page-header";
import { serverApi } from "@/lib/api";
import { coachRights } from "@/lib/roles";
import { SeasonTips } from "./tips-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("seasonPage"))("tipsAction") };
}

/**
 * Saison › Trainingstipps: what to train next comes from the analysis, so it sits with the season
 * (K21), for Trainer and Co-Trainer, whether Teamleben is on or not. The training plan (Teamleben)
 * shows the same tips on top.
 */
export default async function SeasonTipsPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const ts = await getTranslations("seasonPage");
  const tt = await getTranslations("training");
  const tshell = await getTranslations("shell");
  const client = await serverApi();
  const [team, org] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: teamId } } }),
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
  ]);
  const base = `/app/${orgId}/teams/${teamId}`;
  // planning a unit is for Trainer and Co-Trainer; everyone else finds the season itself
  if (!coachRights(org.data?.my_role, team.data?.my_role)) return <Replace to={`${base}/season`} />;
  const eyebrow = [tshell("season"), team.data?.current_season?.label, team.data?.name].filter(Boolean).join(" · ");
  return (
    <div className="space-y-6">
      <Link href={`${base}/season`} className="-mb-3 inline-flex min-h-11 items-center gap-1 text-[15px] font-bold text-ink" data-testid="tips-back">
        <ChevronLeft aria-hidden className="size-4" />
        {tshell("season")}
      </Link>
      <PageHeader eyebrow={eyebrow} title={ts("tipsAction")} />
      <p className="m-0 max-w-[60ch] text-[17px] text-ink-2">{tt("hintTips")}</p>
      <SeasonTips orgId={orgId} teamId={teamId} tasks={Boolean(team.data?.settings.team_features)} />
    </div>
  );
}

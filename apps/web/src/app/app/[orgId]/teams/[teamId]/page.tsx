import Link from "next/link";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { RosterEditor } from "@/components/roster/roster-editor";
import { serverApi } from "@/lib/api";

export default async function RosterPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const client = await serverApi();
  const [team, org, official] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: teamId } } }),
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/official", { params: { path: { org_id: orgId, team_id: teamId } } }),
  ]);
  const t = await getTranslations("official");
  if (!team.data || !org.data) notFound();
  const canEdit = org.data.my_role === "org_admin" || team.data.my_role === "coach";
  // suggestions from the official data wait for an organiser: one line above the squad
  const open = official.data?.linked ? (official.data.open_suggestions ?? 0) : 0;
  return team.data.current_season ? (
    <div className="space-y-6">
      {open > 0 && (
        <p className="text-sm" data-testid="official-open">
          <Link href={`/app/${orgId}/teams/${teamId}/official`} className="font-medium underline decoration-resin decoration-[5px] underline-offset-[5px]">
            {t("openLine", { n: open })}
          </Link>
        </p>
      )}
      <RosterEditor orgId={orgId} teamId={teamId} seasonId={team.data.current_season.id} canEdit={canEdit} />
    </div>
  ) : null;
}

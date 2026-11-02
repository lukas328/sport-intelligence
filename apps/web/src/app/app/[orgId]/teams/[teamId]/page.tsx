import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { RosterEditor } from "@/components/roster/roster-editor";
import { serverApi } from "@/lib/api";

type Params = { params: Promise<{ orgId: string; teamId: string }> };

async function load(orgId: string, teamId: string) {
  const client = await serverApi();
  const [team, org] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: teamId } } }),
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
  ]);
  return { team: team.data, org: org.data };
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { orgId, teamId } = await params;
  const { team } = await load(orgId, teamId);
  return { title: team?.name };
}

export default async function TeamPage({ params }: Params) {
  const { orgId, teamId } = await params;
  const t = await getTranslations();
  const { team, org } = await load(orgId, teamId);
  if (!team || !org) notFound();
  const canEdit = org.my_role === "org_admin" || team.my_role === "coach";
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">{team.name}</h1>
        {team.current_season && (
          <p className="text-sm text-muted">{t("roster.season", { label: team.current_season.label })}</p>
        )}
      </header>
      {team.current_season && (
        <RosterEditor orgId={orgId} teamId={teamId} seasonId={team.current_season.id} canEdit={canEdit} />
      )}
    </div>
  );
}

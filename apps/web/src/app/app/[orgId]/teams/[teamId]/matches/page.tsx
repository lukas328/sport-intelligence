import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { MatchesView } from "./matches-view";

export async function generateMetadata() {
  return { title: (await getTranslations("matches"))("title") };
}

export default async function MatchesPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const client = await serverApi();
  const path = { params: { path: { org_id: orgId, team_id: teamId } } };
  const [matches, team, org] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/matches", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", path),
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
  ]);
  const canWrite = org.data?.my_role === "org_admin" || ["coach", "analyst", "team_manager"].includes(team.data?.my_role ?? "");
  return <MatchesView orgId={orgId} teamId={teamId} matches={matches.data ?? []} canWrite={canWrite} />;
}

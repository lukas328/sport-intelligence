import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { worksWithVideo } from "@/lib/roles";
import { MatchesView } from "./matches-view";

export async function generateMetadata() {
  return { title: (await getTranslations("matches"))("title") };
}

export default async function MatchesPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const client = await serverApi();
  const path = { params: { path: { org_id: orgId, team_id: teamId } } };
  const [matches, team, org] = await Promise.all([
    // with the videos of opponents against other teams (K3): listed here, not in the season
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/matches", { params: { ...path.params, query: { scouting: true } } }),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", path),
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
  ]);
  // players upload and add matches too (K18)
  const canWrite = worksWithVideo(org.data?.my_role, team.data?.my_role);
  return <MatchesView orgId={orgId} teamId={teamId} teamName={team.data?.name ?? ""} matches={matches.data ?? []} canWrite={canWrite} />;
}

import { notFound } from "next/navigation";
import { RosterEditor } from "@/components/roster/roster-editor";
import { serverApi } from "@/lib/api";

export default async function RosterPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const client = await serverApi();
  const [team, org] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: teamId } } }),
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
  ]);
  if (!team.data || !org.data) notFound();
  const canEdit = org.data.my_role === "org_admin" || team.data.my_role === "coach";
  return team.data.current_season ? (
    <RosterEditor orgId={orgId} teamId={teamId} seasonId={team.data.current_season.id} canEdit={canEdit} />
  ) : null;
}

import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { PlayLibrary } from "./play-library";

export default async function PlaysPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const t = await getTranslations("tactics");
  const client = await serverApi();
  const path = { params: { path: { org_id: orgId, team_id: teamId } } };
  const [plays, team, org] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/plays", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", path),
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
  ]);
  const staff = org.data?.my_role === "org_admin" || ["coach", "analyst"].includes(team.data?.my_role ?? "");
  return (
    <div className="space-y-6">
      <h2 className="sr-only">{t("title")}</h2>
      <PlayLibrary orgId={orgId} teamId={teamId} plays={plays.data ?? []} staff={staff} />
    </div>
  );
}

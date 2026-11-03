import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import Link from "next/link";
import { PlayEditor } from "@/components/tactics/play-editor";
import { serverApi } from "@/lib/api";

export default async function PlayPage({ params }: { params: Promise<{ orgId: string; playId: string }> }) {
  const { orgId, playId } = await params;
  const t = await getTranslations("tactics");
  const client = await serverApi();
  const play = await client.GET("/v1/orgs/{org_id}/plays/{play_id}", { params: { path: { org_id: orgId, play_id: playId } } });
  if (!play.data) notFound();
  const [team, org] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: play.data.team_id } } }),
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
  ]);
  const staff = org.data?.my_role === "org_admin" || ["coach", "analyst"].includes(team.data?.my_role ?? "");
  const source = play.data.source as { match_id: string; t_ms: number } | null;
  return (
    <div className="space-y-4">
      <p className="text-sm">
        <Link className="text-muted underline" href={`/app/${orgId}/teams/${play.data.team_id}/plays`}>
          {t("title")}
        </Link>
      </p>
      <h1 className="text-2xl font-semibold">{play.data.name}</h1>
      <PlayEditor orgId={orgId} teamId={play.data.team_id} play={play.data} editable={staff} source={source} />
    </div>
  );
}

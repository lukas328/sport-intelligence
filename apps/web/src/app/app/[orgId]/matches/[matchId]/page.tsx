import { getTranslations } from "next-intl/server";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { serverApi } from "@/lib/api";
import { canDelete, worksWithVideo } from "@/lib/roles";
import { MatchView } from "./match-view";

type Params = { params: Promise<{ orgId: string; matchId: string }> };

async function load(orgId: string, matchId: string) {
  const client = await serverApi();
  const { data: match } = await client.GET("/v1/orgs/{org_id}/matches/{match_id}", {
    params: { path: { org_id: orgId, match_id: matchId } },
  });
  if (!match) return null;
  const [team, org] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: match.team_id } } }),
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
  ]);
  return { match, team: team.data, org: org.data };
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { orgId, matchId } = await params;
  const data = await load(orgId, matchId);
  if (!data) return {};
  if (!data.match.opponent) return { title: `${(await getTranslations("matches"))("training")}: ${data.team?.name ?? ""}` };
  return { title: `${data.team?.name ?? ""} vs ${data.match.opponent.name}` };
}

export default async function MatchPage({ params }: Params) {
  const { orgId, matchId } = await params;
  const data = await load(orgId, matchId);
  if (!data?.team || !data.org) notFound();
  // Trainer, Co-Trainer and players work with the video; deleting is for the staff (K18)
  return (
    <MatchView
      orgId={orgId}
      initial={data.match}
      teamName={data.team.name}
      staff={worksWithVideo(data.org.my_role, data.team.my_role)}
      canDelete={canDelete(data.org.my_role, data.team.my_role)}
    />
  );
}

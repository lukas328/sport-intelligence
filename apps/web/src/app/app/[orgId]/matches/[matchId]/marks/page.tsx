import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { MarksView } from "./marks-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("marks"))("title") };
}

export default async function MarksPage({ params }: { params: Promise<{ orgId: string; matchId: string }> }) {
  const { orgId, matchId } = await params;
  const { data: match } = await (await serverApi()).GET("/v1/orgs/{org_id}/matches/{match_id}", {
    params: { path: { org_id: orgId, match_id: matchId } },
  });
  const client = await serverApi();
  const team = match ? (await client.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: match.team_id } } })).data : null;
  return (
    <MarksView
      orgId={orgId}
      matchId={matchId}
      teamId={match?.team_id ?? ""}
      own={team?.name ?? ""}
      opp={match?.opponent?.name ?? ""}
      kickoffAt={match?.kickoff_at ?? null}
    />
  );
}

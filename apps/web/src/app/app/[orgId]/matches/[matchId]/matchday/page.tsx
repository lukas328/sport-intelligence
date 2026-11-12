import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { LiveClient } from "../live/client";
import { MarksView } from "../marks/marks-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("live"))("title") };
}

/**
 * Spieltag (SPEC 7.11): courtside capture, full screen. One address for both levels that exist
 * today: score and team events (default) and quick marks (?mode=marks). The old /live and /marks
 * routes redirect here.
 */
export default async function MatchdayPage({
  params,
  searchParams,
}: {
  params: Promise<{ orgId: string; matchId: string }>;
  searchParams: Promise<{ mode?: string }>;
}) {
  const { orgId, matchId } = await params;
  if ((await searchParams).mode !== "marks") return <LiveClient orgId={orgId} matchId={matchId} />;
  const client = await serverApi();
  const { data: match } = await client.GET("/v1/orgs/{org_id}/matches/{match_id}", { params: { path: { org_id: orgId, match_id: matchId } } });
  const team = match ? (await client.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: match.team_id } } })).data : null;
  return (
    <MarksView
      orgId={orgId}
      matchId={matchId}
      teamId={match?.team_id ?? ""}
      own={team?.name ?? ""}
      opp={match?.opponent?.name ?? ""}
      kickoffAt={match?.kickoff_at ?? null}
      oppColor={match?.opponent_colors?.color ?? null}
    />
  );
}

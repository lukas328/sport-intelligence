import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { ScoutingView } from "./scouting-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("scouting"))("title") };
}

/**
 * The old preparation report. The opponent lives in «Gegner» now (SPEC 6, UX test B32): the route
 * leads to the opponent's page, or back to the match without a known opponent.
 */
export default async function ScoutingPage({ params }: { params: Promise<{ orgId: string; matchId: string }> }) {
  const { orgId, matchId } = await params;
  const { data: match } = await (await serverApi()).GET("/v1/orgs/{org_id}/matches/{match_id}", { params: { path: { org_id: orgId, match_id: matchId } } });
  if (match?.opponent?.id) redirect(`/app/${orgId}/opponents/${match.opponent.id}`);
  if (match) redirect(`/app/${orgId}/matches/${matchId}`);
  return <ScoutingView orgId={orgId} matchId={matchId} />;
}

import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { ScoutingView } from "./scouting-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("scouting"))("title") };
}

export default async function ScoutingPage({ params }: { params: Promise<{ orgId: string; matchId: string }> }) {
  const { orgId, matchId } = await params;
  return <ScoutingView orgId={orgId} matchId={matchId} />;
}

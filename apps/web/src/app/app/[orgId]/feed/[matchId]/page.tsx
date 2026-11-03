import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { FeedView } from "./feed-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("feed"))("title") };
}

export default async function FeedMatchPage({
  params,
  searchParams,
}: {
  params: Promise<{ orgId: string; matchId: string }>;
  searchParams: Promise<{ player?: string }>;
}) {
  const { orgId, matchId } = await params;
  const { player } = await searchParams;
  return <FeedView orgId={orgId} matchId={matchId} playerId={player ?? null} />;
}

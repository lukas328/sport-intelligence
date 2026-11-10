import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { SeasonLineView } from "./season-line";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("seasonLine"))("title") };
}

export default async function PlayerPage({ params }: { params: Promise<{ orgId: string; teamId: string; playerId: string }> }) {
  const { orgId, teamId, playerId } = await params;
  return <SeasonLineView orgId={orgId} teamId={teamId} playerId={playerId} />;
}

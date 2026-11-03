import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { LiveClient } from "./client";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("live"))("title") };
}

export default async function LivePage({ params }: { params: Promise<{ orgId: string; matchId: string }> }) {
  const { orgId, matchId } = await params;
  return <LiveClient orgId={orgId} matchId={matchId} />;
}

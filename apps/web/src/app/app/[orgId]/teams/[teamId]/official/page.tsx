import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { OfficialInbox } from "./official-inbox";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("official"))("title") };
}

export default async function TeamOfficialPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  return <OfficialInbox orgId={orgId} teamId={teamId} />;
}

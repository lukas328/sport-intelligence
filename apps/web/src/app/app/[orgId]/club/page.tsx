import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { ClubSection } from "../settings/settings-view";
import { loadSettings } from "../settings/load";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("settings"))("club") };
}

/** Name, colours, crest. Coaches start on the teams tab. */
export default async function ClubPage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  const { org, isAdmin } = await loadSettings(orgId);
  if (!isAdmin) redirect(`/app/${orgId}/club/teams`);
  return <ClubSection org={org} />;
}

import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { TeamFeaturesGate } from "@/components/shell/team-features-gate";
import { FeedList } from "./feed-list";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("feed"))("title") };
}

export default async function FeedPage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  return (
    <TeamFeaturesGate>
      <FeedList orgId={orgId} />
    </TeamFeaturesGate>
  );
}

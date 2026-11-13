import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { TeamFeaturesGate } from "@/components/shell/team-features-gate";
import { MyConsents } from "./my-consents";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("consents"))("title") };
}

export default async function ConsentsPage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  return (
    <TeamFeaturesGate>
      <MyConsents orgId={orgId} />
    </TeamFeaturesGate>
  );
}

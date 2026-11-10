import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { PrivacySection } from "@/components/privacy/privacy-section";
import { loadSettings } from "../../settings/load";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("privacy"))("title") };
}

export default async function MeDataPage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  const { org, me, isAdmin } = await loadSettings(orgId);
  return <PrivacySection orgId={org.id} orgName={org.name} isAdmin={isAdmin} hasPassword={me.has_password ?? true} />;
}

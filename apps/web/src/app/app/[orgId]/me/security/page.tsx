import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AccountSection } from "@/components/account-section";
import { SecuritySection } from "../../settings/settings-view";
import { loadSettings } from "../../settings/load";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("settings"))("security") };
}

export default async function MeSecurityPage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  const { me, isAdmin } = await loadSettings(orgId);
  // password and signed-in devices, then two-factor sign-in (A13)
  return (
    <>
      <AccountSection me={me} />
      <SecuritySection me={me} isAdmin={isAdmin} />
    </>
  );
}

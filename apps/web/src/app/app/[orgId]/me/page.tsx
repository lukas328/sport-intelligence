import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AccountSection } from "@/components/account-section";
import { ProfileEditor } from "../profile/profile-editor";
import { loadSettings } from "../settings/load";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("settings"))("me") };
}

export default async function MePage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  const { me } = await loadSettings(orgId);
  return (
    <>
      <AccountSection me={me} />
      <ProfileEditor orgId={orgId} />
    </>
  );
}

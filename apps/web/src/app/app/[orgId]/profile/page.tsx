import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { ProfileEditor } from "./profile-editor";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("profile"))("title") };
}

export default async function ProfilePage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  return <ProfileEditor orgId={orgId} />;
}

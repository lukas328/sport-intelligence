import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { PresentationList } from "./presentation-list";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("presentations"))("title") };
}

export default async function Page({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  return <PresentationList orgId={orgId} teamId={teamId} />;
}

import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AssistantView } from "./assistant-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("assistant"))("title") };
}

export default async function AssistantPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  return <AssistantView orgId={orgId} teamId={teamId} />;
}

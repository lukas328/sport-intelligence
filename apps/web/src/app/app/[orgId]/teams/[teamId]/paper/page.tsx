import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { PaperView } from "./paper-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("paper"))("photoTitle") };
}

export default async function PaperPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  return <PaperView orgId={orgId} teamId={teamId} />;
}

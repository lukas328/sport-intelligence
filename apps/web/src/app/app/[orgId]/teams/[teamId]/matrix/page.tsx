import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { MatrixView } from "./matrix-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("matrix"))("title") };
}

export default async function MatrixPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  return <MatrixView orgId={orgId} teamId={teamId} />;
}

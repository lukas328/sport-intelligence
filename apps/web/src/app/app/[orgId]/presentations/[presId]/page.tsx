import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { PresentationEditor } from "./editor";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("presentations"))("title") };
}

export default async function Page({ params }: { params: Promise<{ orgId: string; presId: string }> }) {
  const { orgId, presId } = await params;
  return <PresentationEditor orgId={orgId} presId={presId} />;
}

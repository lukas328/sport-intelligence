import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Presenter } from "./presenter";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("presentations"))("present") };
}

export default async function Page({ params }: { params: Promise<{ orgId: string; presId: string }> }) {
  const { orgId, presId } = await params;
  return <Presenter orgId={orgId} presId={presId} />;
}

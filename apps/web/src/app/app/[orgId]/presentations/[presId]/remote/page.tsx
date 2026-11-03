import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Remote } from "./remote";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("presentations"))("remote") };
}

export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ orgId: string; presId: string }>;
  searchParams: Promise<{ k?: string }>;
}) {
  const { orgId, presId } = await params;
  const { k } = await searchParams;
  return <Remote orgId={orgId} presId={presId} pairKey={k ?? ""} />;
}

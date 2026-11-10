import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { BillingSection } from "@/components/billing/billing-section";
import { loadSettings } from "../../settings/load";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("billing"))("title") };
}

export default async function ClubBillingPage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  const { org, isAdmin } = await loadSettings(orgId);
  if (!isAdmin) notFound();
  return <BillingSection orgId={org.id} />;
}

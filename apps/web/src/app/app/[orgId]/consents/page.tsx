import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { MyConsents } from "./my-consents";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("consents"))("title") };
}

export default async function ConsentsPage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  return <MyConsents orgId={orgId} />;
}

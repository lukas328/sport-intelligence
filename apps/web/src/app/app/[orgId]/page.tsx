import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { TodayView } from "./today-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("shell"))("today") };
}

export default async function TodayPage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  return <TodayView orgId={orgId} />;
}

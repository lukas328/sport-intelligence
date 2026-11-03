import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { ScheduleView } from "./schedule-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("schedule"))("title") };
}

export default async function SchedulePage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  return <ScheduleView orgId={orgId} />;
}

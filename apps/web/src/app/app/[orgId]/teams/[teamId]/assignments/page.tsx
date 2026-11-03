import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { TeamAssignments } from "./team-assignments";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("assignments"))("team") };
}

export default async function TeamAssignmentsPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  return <TeamAssignments orgId={orgId} teamId={teamId} />;
}

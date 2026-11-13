import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { TeamFeaturesGate } from "@/components/shell/team-features-gate";
import { TeamAssignments } from "./team-assignments";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("assignments"))("team") };
}

export default async function TeamAssignmentsPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  return (
    <TeamFeaturesGate>
      <TeamAssignments orgId={orgId} teamId={teamId} />
    </TeamFeaturesGate>
  );
}

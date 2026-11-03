import { TeamAssignments } from "./team-assignments";

export default async function TeamAssignmentsPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  return <TeamAssignments orgId={orgId} teamId={teamId} />;
}

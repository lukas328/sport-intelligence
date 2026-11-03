import { MyAssignments } from "./my-assignments";

export default async function AssignmentsPage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  return <MyAssignments orgId={orgId} />;
}

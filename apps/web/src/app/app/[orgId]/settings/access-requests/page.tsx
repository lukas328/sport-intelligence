import { redirect } from "next/navigation";

export default async function AccessRequestsPage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  redirect(`/app/${orgId}/club/federation`);
}

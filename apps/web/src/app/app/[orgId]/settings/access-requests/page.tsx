import { redirect } from "next/navigation";

/** The notification for an access request links here: the requests sit in the settings. */
export default async function AccessRequestsPage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  redirect(`/app/${orgId}/settings#official-section`);
}

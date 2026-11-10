import { redirect } from "next/navigation";

/**
 * Prüfen (SPEC 7.5): the check queue of a match. Until it has its own full-screen page it opens
 * the review of the match workspace (goal candidates, then shots), which is full screen already.
 */
export default async function CheckPage({ params }: { params: Promise<{ orgId: string; matchId: string }> }) {
  const { orgId, matchId } = await params;
  redirect(`/app/${orgId}/matches/${matchId}?tab=video&check=1`);
}

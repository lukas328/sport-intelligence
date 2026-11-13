import { redirect } from "next/navigation";

/** Old address of the courtside capture: now Spieltag (SPEC section 6). */
export default async function LivePage({ params }: { params: Promise<{ orgId: string; matchId: string }> }) {
  const { orgId, matchId } = await params;
  redirect(`/app/${orgId}/matches/${matchId}/matchday?mode=detail`);
}

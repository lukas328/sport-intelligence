import { redirect } from "next/navigation";

/** Old address of the courtside marks: now Spieltag, quick marks level (SPEC section 6). */
export default async function MarksPage({ params }: { params: Promise<{ orgId: string; matchId: string }> }) {
  const { orgId, matchId } = await params;
  redirect(`/app/${orgId}/matches/${matchId}/matchday?mode=marks`);
}

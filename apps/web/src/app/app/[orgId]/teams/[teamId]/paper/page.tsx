import { redirect } from "next/navigation";

/** Old address of the match report photo. The paper report is a file of its match now (K19,
 * «Dateien zum Spiel»); the official report of handball.ch comes by itself: to Spiele. */
export default async function PaperPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  redirect(`/app/${orgId}/teams/${teamId}/matches`);
}

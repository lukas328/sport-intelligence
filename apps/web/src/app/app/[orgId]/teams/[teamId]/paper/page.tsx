import { redirect } from "next/navigation";

/** Old address of the match report photo: now the dialog "Spielbericht hinzufügen" on Spiele. */
export default async function PaperPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  redirect(`/app/${orgId}/teams/${teamId}/matches?report=1`);
}

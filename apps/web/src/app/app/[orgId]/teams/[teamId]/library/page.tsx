import { redirect } from "next/navigation";

/** Old address of the library: now the collections tab of Szenen (SPEC section 6). */
export default async function LibraryPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  redirect(`/app/${orgId}/teams/${teamId}/collections`);
}

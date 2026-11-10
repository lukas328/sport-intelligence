import { redirect } from "next/navigation";

/** Old address of the scene search: now Szenen (SPEC section 6). */
export default async function SearchPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  redirect(`/app/${orgId}/teams/${teamId}/scenes`);
}

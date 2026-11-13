import { redirect } from "next/navigation";

/** Old address of the scene search: now Szenen (SPEC section 6). Filters in the query stay. */
export default async function SearchPage({
  params,
  searchParams,
}: {
  params: Promise<{ orgId: string; teamId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { orgId, teamId } = await params;
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(await searchParams)) for (const one of [v].flat()) if (one != null) q.append(k, one);
  const qs = q.toString();
  redirect(`/app/${orgId}/teams/${teamId}/scenes${qs ? `?${qs}` : ""}`);
}

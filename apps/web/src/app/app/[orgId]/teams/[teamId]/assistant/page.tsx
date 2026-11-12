import { redirect } from "next/navigation";

/**
 * «Suchen» is the scene search (SPEC 9, UX test B02): the old assistant address leads there and
 * hands the question over as text (its words become chips). AssistantView stays in the code for
 * an installation with a language model.
 */
export default async function AssistantPage({ params, searchParams }: { params: Promise<{ orgId: string; teamId: string }>; searchParams: Promise<{ q?: string }> }) {
  const { orgId, teamId } = await params;
  const { q } = await searchParams;
  redirect(`/app/${orgId}/teams/${teamId}/scenes${q ? `?q=${encodeURIComponent(q)}` : "?focus=1"}`);
}

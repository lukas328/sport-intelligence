import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { MatrixView } from "./matrix-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("matrix"))("title") };
}

/**
 * The old pivot table. «Als Tabelle» now shows the scene answer as rows in Szenen (SPEC 6, UX test
 * B21, B32): the route leads there; the pivot itself stays reachable with ?pivot=1.
 */
export default async function MatrixPage({ params, searchParams }: { params: Promise<{ orgId: string; teamId: string }>; searchParams: Promise<{ pivot?: string }> }) {
  const { orgId, teamId } = await params;
  if ((await searchParams).pivot !== "1") redirect(`/app/${orgId}/teams/${teamId}/scenes?view=table`);
  const { data: team } = await (await serverApi()).GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: teamId } } });
  return <MatrixView orgId={orgId} teamId={teamId} teamName={team?.name ?? ""} seasonId={team?.current_season?.id ?? null} />;
}

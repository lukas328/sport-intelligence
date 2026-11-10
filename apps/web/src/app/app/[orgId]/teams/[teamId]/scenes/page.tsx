import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { SearchView } from "../search/search-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("shell"))("scenes") };
}

/** Szenen (SPEC 7.6): the search field is the page. */
export default async function ScenesPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const { data: team } = await (await serverApi()).GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: teamId } } });
  return <SearchView orgId={orgId} teamId={teamId} teamName={team?.name ?? ""} seasonId={team?.current_season?.id ?? null} />;
}

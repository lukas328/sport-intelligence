import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { LibraryView } from "./library-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("shell"))("collections") };
}

/** Sammlungen (SPEC 7.6, 7.7): playlists and presentations until they become one collection. */
export default async function CollectionsPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const client = await serverApi();
  const path = { params: { path: { org_id: orgId, team_id: teamId } } };
  const [playlists, presentations] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/playlists", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/presentations", path),
  ]);
  return (
    <LibraryView
      base={`/app/${orgId}/teams/${teamId}`}
      orgBase={`/app/${orgId}`}
      playlists={playlists.data ?? []}
      presentations={presentations.data ?? []}
    />
  );
}

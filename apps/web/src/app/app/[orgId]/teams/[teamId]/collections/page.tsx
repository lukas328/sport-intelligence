import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { CollectionList } from "@/components/collections/collection-list";
import { LibraryView } from "./library-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("shell"))("collections") };
}

/** Sammlungen (SPEC 7.6, 7.7): every collection (older playlists and presentations read as one),
 * then the shelves that still create playlists and presentations. */
export default async function CollectionsPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const client = await serverApi();
  const path = { params: { path: { org_id: orgId, team_id: teamId } } };
  const [playlists, presentations, collections] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/playlists", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/presentations", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/collections", path),
  ]);
  return (
    <div className="space-y-12">
    <CollectionList orgId={orgId} items={collections.data ?? []} />
    <LibraryView
      base={`/app/${orgId}/teams/${teamId}`}
      orgBase={`/app/${orgId}`}
      playlists={playlists.data ?? []}
      presentations={presentations.data ?? []}
    />
    </div>
  );
}

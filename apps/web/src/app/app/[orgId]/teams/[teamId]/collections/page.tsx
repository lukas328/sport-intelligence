import type { Metadata } from "next";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { buttonClass } from "@/components/ui/button";
import { serverApi } from "@/lib/api";
import { CollectionList } from "@/components/collections/collection-list";
import { worksWithVideo } from "@/lib/roles";
import { LibraryView } from "./library-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("shell"))("collections") };
}

/** Sammlungen (SPEC 7.6, 7.7): every collection (older playlists and presentations read as one),
 * then the shelves that still create playlists and presentations. Empty: one sentence what a
 * collection is for and the one way to the first (K8). */
export default async function CollectionsPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const client = await serverApi();
  const path = { params: { path: { org_id: orgId, team_id: teamId } } };
  const [playlists, presentations, collections, matches, team, org] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/playlists", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/presentations", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/collections", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/matches", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", path),
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
  ]);
  const base = `/app/${orgId}/teams/${teamId}`;
  const empty = (collections.data ?? []).length === 0 && (playlists.data ?? []).length === 0 && (presentations.data ?? []).length === 0;
  if (empty) {
    const t = await getTranslations("collections");
    const ta = await getTranslations("anlauf");
    const video = (matches.data ?? []).some((m) => m.has_video);
    const canWrite = worksWithVideo(org.data?.my_role, team.data?.my_role);
    return (
      <section className="max-w-[60ch] space-y-4" data-testid="collections-empty">
        <p className="font-slant m-0 text-[28px] leading-tight md:text-[34px]">{t("emptyTitle")}</p>
        <p className="m-0 text-[17px]">{video ? t("emptyText") : t("emptyNoVideo")}</p>
        {video ? (
          <Link href={`${base}/scenes`} className={buttonClass("primary")}>
            {t("emptyToScenes")}
          </Link>
        ) : (
          canWrite && (
            <Link href={`${base}/matches?upload=1`} className={buttonClass("primary")}>
              {ta("uploadVideo")}
            </Link>
          )
        )}
      </section>
    );
  }
  return (
    <div className="space-y-12">
      <CollectionList orgId={orgId} items={collections.data ?? []} />
      <LibraryView base={base} orgBase={`/app/${orgId}`} playlists={playlists.data ?? []} presentations={presentations.data ?? []} />
    </div>
  );
}

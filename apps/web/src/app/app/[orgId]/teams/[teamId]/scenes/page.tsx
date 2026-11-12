import type { Metadata } from "next";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { linkClass, SectionHead } from "@/components/anlauf/blocks";
import { CollectionList } from "@/components/collections/collection-list";
import { serverApi } from "@/lib/api";
import { SearchView } from "../search/search-view";
import { SceneTiles } from "./scene-tiles";
import { ScenesHead } from "./scenes-head";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("shell"))("scenes") };
}

/** Szenen (SPEC 7.6): the count in the Seitenkopf, the search, the goals as scene tiles, the
 * Sammlungen. No tabs: plays and the table are links next to the Sammlungen. */
export default async function ScenesPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const t = await getTranslations("anlauf");
  const client = await serverApi();
  const path = { params: { path: { org_id: orgId, team_id: teamId } } };
  const [{ data: team }, { data: matches = [] }, { data: collections = [] }] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/matches", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/collections", path),
  ]);
  const withVideo = matches.filter((m) => m.has_video).sort((a, b) => b.kickoff_at.localeCompare(a.kickoff_at));
  const base = `/app/${orgId}/teams/${teamId}`;
  return (
    <div>
      <ScenesHead orgId={orgId} teamId={teamId} matches={withVideo.length} />
      <div className="space-y-12">
        <SearchView orgId={orgId} teamId={teamId} teamName={team?.name ?? ""} seasonId={team?.current_season?.id ?? null} />
        {withVideo.length > 0 && <SceneTiles orgId={orgId} matches={withVideo.slice(0, 3)} />}
        <div className="grid gap-12 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div>
            <SectionHead
              title={<span id="all-collections">{t("collections")}</span>}
              action={
                <Link href={`${base}/collections`} className={linkClass}>
                  {t("allCollections")}
                </Link>
              }
            />
            <CollectionList orgId={orgId} items={collections} heading={false} />
          </div>
          <div>
            <SectionHead as="h3" title={t("more")} />
            <p className="flex flex-wrap gap-4 text-[15px]">
              <Link href={`${base}/plays`} className={linkClass}>
                {t("plays")}
              </Link>
              <Link href={`${base}/matrix`} className={linkClass}>
                {t("matrix")}
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

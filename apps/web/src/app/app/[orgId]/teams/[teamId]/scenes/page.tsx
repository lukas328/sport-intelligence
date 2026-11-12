import type { Metadata } from "next";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { linkClass, SectionHead } from "@/components/anlauf/blocks";
import { CollectionList } from "@/components/collections/collection-list";
import { serverApi } from "@/lib/api";
import { SearchView } from "../search/search-view";
import { ScenesHead } from "./scenes-head";
import { ScenesView } from "./scenes-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("shell"))("scenes") };
}

/** Szenen (SPEC 7.6): the count in the Seitenkopf, the search with chips, the answer, the scenes
 * as tiles; Sammlungen and Highlights at the side. The event list, saved searches and own tags
 * are behind «Mehr»; plays and the table are links. */
export default async function ScenesPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const t = await getTranslations("scenesPage");
  const ta = await getTranslations("anlauf");
  const client = await serverApi();
  const path = { params: { path: { org_id: orgId, team_id: teamId } } };
  const [{ data: team }, { data: matches = [] }, { data: collections = [] }] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/matches", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/collections", path),
  ]);
  const withVideo = matches.filter((m) => m.has_video).sort((a, b) => b.kickoff_at.localeCompare(a.kickoff_at));
  const last = withVideo[0];
  const { data: highlights = [] } = last
    ? await client.GET("/v1/orgs/{org_id}/matches/{match_id}/highlights", { params: { path: { org_id: orgId, match_id: last.id } } })
    : { data: [] };
  const base = `/app/${orgId}/teams/${teamId}`;
  const side = (
    <>
      <div>
        <SectionHead
          title={<span id="all-collections">{t("collections")}</span>}
          action={
            <Link href={`${base}/collections`} className={linkClass}>
              {t("newCollection")}
            </Link>
          }
        />
        <CollectionList orgId={orgId} items={collections} heading={false} />
      </div>
      <div>
        <SectionHead as="h3" title={t("highlights")} note={t("highlightsNote")} />
        {highlights.length > 0 && last ? (
          <ul className="m-0 list-none p-0">
            {highlights.map((h) => (
              <li key={h.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 border-t border-rule py-3.5">
                <span>
                  <span className="font-slant block text-xl">{last.opponent_name}</span>
                  <span className="text-[15px] text-ink-2">{t("highlightLine", { n: h.clip_ids.length, format: h.format })}</span>
                </span>
                <Link href={`/app/${orgId}/matches/${last.id}?tab=spiel`} className={linkClass}>
                  {t("share")}
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[15px] text-ink-2">{t("noHighlights")}</p>
        )}
      </div>
      <p className="flex flex-wrap gap-4 text-[15px]">
        <Link href={`${base}/collections`} className={linkClass}>
          {ta("allCollections")}
        </Link>
        <Link href={`${base}/plays`} className={linkClass}>
          {ta("plays")}
        </Link>
        <Link href={`${base}/matrix`} className={linkClass}>
          {ta("matrix")}
        </Link>
      </p>
    </>
  );
  return (
    <div>
      <ScenesHead orgId={orgId} teamId={teamId} matches={withVideo.length} />
      <ScenesView orgId={orgId} teamId={teamId} matches={matches} side={side} />
      <details className="mt-16 border-t-2 border-ink pt-4">
        <summary className="min-h-11 cursor-pointer content-center font-bold underline decoration-[1.5px] underline-offset-4" data-testid="scenes-more">
          {t("moreTools")}
        </summary>
        <div className="mt-6">
          <SearchView orgId={orgId} teamId={teamId} teamName={team?.name ?? ""} seasonId={team?.current_season?.id ?? null} />
        </div>
      </details>
    </div>
  );
}

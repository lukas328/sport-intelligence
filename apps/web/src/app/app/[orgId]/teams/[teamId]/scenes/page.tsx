import type { Metadata } from "next";
import { Search } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { linkClass, SectionHead } from "@/components/anlauf/blocks";
import { CollectionList } from "@/components/collections/collection-list";
import { buttonClass } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { serverApi } from "@/lib/api";
import { worksWithVideo } from "@/lib/roles";
import { SearchView } from "../search/search-view";
import { ScenesHead } from "./scenes-head";
import { ScenesView } from "./scenes-view";
import { CollectionBack } from "./collection-back";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("shell"))("scenes") };
}

/** Szenen (SPEC 7.6): the count in the Seitenkopf, the search with chips, the answer, the scenes
 * as tiles; Sammlungen and Highlights at the side. The event list, saved searches and own tags
 * are behind «Mehr»; plays and the table are links. */
export default async function ScenesPage({
  params,
  searchParams,
}: {
  params: Promise<{ orgId: string; teamId: string }>;
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const { orgId, teamId } = await params;
  // a question asked from elsewhere (?q, ?chips, ?view) is read by the search itself; without a
  // video there is nothing to answer it with. ?collection= opens the scenes for a collection
  // («Szene dazu»): found scenes go into it, a link leads back (A5)
  const { collection: intoId } = await searchParams;
  const t = await getTranslations("scenesPage");
  const ta = await getTranslations("anlauf");
  const client = await serverApi();
  const path = { params: { path: { org_id: orgId, team_id: teamId } } };
  const [{ data: team }, { data: matches = [] }, { data: collections = [] }, { data: into }] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/matches", path),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/collections", path),
    intoId ? client.GET("/v1/orgs/{org_id}/collections/{collection_id}", { params: { path: { org_id: orgId, collection_id: intoId } } }) : Promise.resolve({ data: undefined }),
  ]);
  const target = into && into.editable && into.team_id === teamId ? into : null;
  const back = target ? <CollectionBack href={`/app/${orgId}/collections/${target.id}`} label={t("backToCollection", { title: target.title })} /> : null;
  const withVideo = matches
    .filter((m) => m.has_video)
    .sort((a, b) => b.kickoff_at.localeCompare(a.kickoff_at));
  const last = withVideo[0];
  const { data: highlights = [] } = last
    ? await client.GET("/v1/orgs/{org_id}/matches/{match_id}/highlights", {
        params: { path: { org_id: orgId, match_id: last.id } },
      })
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
              <li
                key={h.id}
                className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 border-t border-rule py-3.5"
              >
                <span>
                  <span className="font-slant block text-xl">{last.opponent_name}</span>
                  <span className="text-[15px] text-ink-2">
                    {t("highlightLine", { n: h.clip_ids.length, format: h.format })}
                  </span>
                </span>
                <Link href={`/app/${orgId}/matches/${last.id}?tab=spiel`} className={linkClass}>
                  {t("share")}
                </Link>
              </li>
            ))}
          </ul>
        ) : last ? (
          // a match with video is there, its highlights are not made yet (UX test B52)
          <p className="text-[15px] text-ink-2">
            {t("noHighlightsYet", { opponent: last.opponent_name ?? "" })}{" "}
            <Link href={`/app/${orgId}/matches/${last.id}?tab=spiel`} className={linkClass}>
              {t("makeHighlights")}
            </Link>
          </p>
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
        {/* the pivot table, kept: «Als Tabelle» above shows the answer as rows */}
        <Link href={`${base}/matrix?pivot=1`} className={linkClass}>
          {ta("matrix")}
        </Link>
      </p>
    </>
  );
  // the event list, saved searches and own tags, behind «Mehr», with or without video
  const more = (
    <details className="mt-16 border-t-2 border-ink pt-4">
      <summary
        className="min-h-11 cursor-pointer content-center font-bold underline decoration-[1.5px] underline-offset-4"
        data-testid="scenes-more"
      >
        {t("moreTools")}
      </summary>
      <div className="mt-6">
        <SearchView
          orgId={orgId}
          teamId={teamId}
          teamName={team?.name ?? ""}
          seasonId={team?.current_season?.id ?? null}
        />
      </div>
    </details>
  );
  // before the first video there is nothing to search (K8, UX test B28): one sentence, what comes,
  // one action; no search, chips, collections or highlights. Spielzüge work without video.
  if (withVideo.length === 0) {
    const { data: org } = await client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } });
    const canWrite = worksWithVideo(org?.my_role, team?.my_role);
    return (
      <div>
        {back}
        <PageHeader title={(await getTranslations("shell"))("scenes")} />
        {/* «Suchen» leads here: the field is there, it says from when it finds something (review R6) */}
        <label className="mb-10 flex min-h-16 max-w-3xl items-center gap-3 border-2 border-rule bg-paper px-[18px] text-xl font-semibold text-ink-2">
          <Search aria-hidden className="size-[22px] shrink-0" strokeWidth={2.2} />
          <span className="sr-only">{t("searchLabel")}</span>
          <input
            disabled
            aria-describedby="scenes-empty-search"
            placeholder={t("placeholder")}
            className="min-w-0 flex-1 cursor-not-allowed bg-transparent font-semibold text-ink-2 outline-none placeholder:text-ink-2"
            data-testid="scene-search"
          />
        </label>
        <section className="max-w-[60ch] space-y-4" data-testid="scenes-empty">
          <p id="scenes-empty-search" className="m-0 text-[15px] font-semibold text-ink-2">
            {t("emptySearch")}
          </p>
          <p className="font-slant m-0 text-[28px] leading-tight md:text-[34px]">{t("emptyTitle")}</p>
          <p className="m-0 text-[17px]">{t("emptyText")}</p>
          {canWrite && (
            <Link href={`${base}/matches?upload=1`} className={buttonClass("primary")}>
              {ta("uploadVideo")}
            </Link>
          )}
          <p className="m-0 pt-4 text-[15px] text-ink-2">
            {t("emptyPlays")}{" "}
            <Link href={`${base}/plays`} className={linkClass}>
              {ta("plays")}
            </Link>
          </p>
        </section>
        {/* the team's collections stay findable here before the first video (A5) */}
        {collections.length > 0 && (
          <section className="mt-12 max-w-3xl" aria-labelledby="all-collections">
            <SectionHead title={<span id="all-collections">{t("collections")}</span>} />
            <CollectionList orgId={orgId} items={collections} heading={false} />
          </section>
        )}
      </div>
    );
  }
  return (
    <div>
      {back}
      <ScenesHead orgId={orgId} teamId={teamId} matches={withVideo.length} />
      <ScenesView orgId={orgId} teamId={teamId} matches={matches} side={side} into={target} />
      {more}
    </div>
  );
}

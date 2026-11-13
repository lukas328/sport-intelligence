import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { SectionHead } from "@/components/anlauf/blocks";
import { buttonClass } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { serverApi } from "@/lib/api";
import { CollectionEditor, CollectionTitle } from "./collection-editor";
import { ShareBox } from "./share-box";

type Params = { params: Promise<{ orgId: string; collectionId: string }> };

async function load(orgId: string, collectionId: string) {
  const { data } = await (await serverApi()).GET("/v1/orgs/{org_id}/collections/{collection_id}", {
    params: { path: { org_id: orgId, collection_id: collectionId } },
  });
  return data;
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { orgId, collectionId } = await params;
  return { title: (await load(orgId, collectionId))?.title ?? "" };
}

const time = (ms: number) => `${Math.floor(ms / 60000)}:${String(Math.round((ms % 60000) / 1000)).padStart(2, "0")}`;

/** Sammlung (SPEC 7.7): the run of scenes, plays and notes; at the side how the link looks in a
 * chat and how often it was opened. */
export default async function CollectionPage({ params }: Params) {
  const { orgId, collectionId } = await params;
  const c = await load(orgId, collectionId);
  if (!c) notFound();
  const t = await getTranslations("collections");
  const client = await serverApi();
  const [{ data: links = [] }, { data: team }, { data: org }] = await Promise.all([
    client.GET("/v1/orgs/{org_id}/teams/{team_id}/share-links", { params: { path: { org_id: orgId, team_id: c.team_id } } }),
    client.GET("/v1/orgs/{org_id}/teams/{team_id}", { params: { path: { org_id: orgId, team_id: c.team_id } } }),
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
  ]);
  const link = links.filter((l) => l.kind === "collection" && l.target_id === c.id && !l.revoked_at).sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
  const base = `/app/${orgId}`;
  const scenes = c.items.filter((i) => i.scene);
  const plays = c.items.filter((i) => i.play);
  const total = scenes.reduce((s, i) => s + Math.max(0, i.scene!.end_ms - i.scene!.start_ms), 0);
  const origin = c.source === "playlist" ? `${base}/playlists/${c.id}` : c.source === "presentation" ? `${base}/presentations/${c.id}` : null;
  const summary = t("summary", { scenes: scenes.length, plays: plays.length, time: time(total) });
  return (
    <div>
      <PageHeader
        eyebrow={[t("title"), c.draft ? t("draft") : null, c.source !== "collection" ? t(`source_${c.source}`) : null].filter(Boolean).join(" · ")}
        title={<CollectionTitle orgId={orgId} collection={c} />}
        actions={
          <>
            <Link href={`${base}/collections/${c.id}/present`} className={buttonClass("secondary")} data-testid="present">
              {t("present")}
            </Link>
            {origin && (
              <Link href={origin} className={buttonClass("ghost")}>
                {t("edit")}
              </Link>
            )}
          </>
        }
      />
      <div className="grid gap-12 lg:grid-cols-[minmax(0,1fr)_340px]">
        <section aria-labelledby="run" className="min-w-0">
          <SectionHead title={<span id="run">{t("run")}</span>} note={summary} />
          <CollectionEditor orgId={orgId} collection={c} />
          <div className="mt-4 flex flex-wrap gap-2.5">
            <Link href={`${base}/teams/${c.team_id}/scenes`} className={buttonClass("secondary", "sm")}>
              {t("addScene")}
            </Link>
            <Link href={`${base}/teams/${c.team_id}/plays`} className={buttonClass("secondary", "sm")}>
              {t("addPlay")}
            </Link>
          </div>
        </section>
        <aside className="flex min-w-0 flex-col gap-8">
          <div>
            <SectionHead as="h2" title={t("inChat")} />
            <div className="bg-[#e4ddd2] p-5">
              <div className="ml-auto max-w-[300px] bg-white p-1.5 text-attn-ink">
                <div className="relative h-[150px] overflow-hidden bg-club p-3.5 text-club-ink shadow-[inset_0_0_0_2px_var(--club-edge)] [clip-path:polygon(0_0,100%_0,100%_84%,0_100%)]">
                  <b className="font-slant block max-w-[80%] text-[26px] leading-[.95]">{c.title}</b>
                </div>
                <p className="m-0 px-1.5 pt-2 text-[15px]">
                  <b className="block text-[15px]">{c.title}</b>
                  {[org?.name, team?.name].filter(Boolean).join(" ")} · {summary}
                </p>
              </div>
            </div>
            <p className="mt-2 text-[15px] text-ink-2">{t("chatHint")}</p>
          </div>
          <ShareBox orgId={orgId} teamId={c.team_id} collectionId={c.id} link={link ?? null} />
        </aside>
      </div>
    </div>
  );
}

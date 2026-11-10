import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { PageHeader } from "@/components/ui/page-header";
import { buttonClass } from "@/components/ui/button";
import { ShareButton } from "@/components/sharing/share-button";
import { serverApi } from "@/lib/api";

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

const time = (ms: number) => `${Math.floor(ms / 60000)}:${String(Math.floor((ms % 60000) / 1000)).padStart(2, "0")}`;

/** Sammlung (SPEC 7.7): the run of scenes, plays and notes. Plain page until the new look. */
export default async function CollectionPage({ params }: Params) {
  const { orgId, collectionId } = await params;
  const c = await load(orgId, collectionId);
  if (!c) notFound();
  const t = await getTranslations("collections");
  const org = `/app/${orgId}`;
  // older objects are changed where they are
  const origin = c.source === "playlist" ? `${org}/playlists/${c.id}` : c.source === "presentation" ? `${org}/presentations/${c.id}` : null;
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow={[t("title"), c.draft ? t("draft") : null, c.source !== "collection" ? t(`source_${c.source}`) : null].filter(Boolean).join(" · ")}
        title={c.title}
        actions={
          <>
            <ShareButton orgId={orgId} teamId={c.team_id} kind="collection" targetId={c.id} />
            <Link href={`${org}/collections/${c.id}/present`} className={buttonClass("secondary")}>
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
      <section aria-labelledby="run" className="space-y-3">
        <h2 id="run" className="text-lg font-bold">
          {t("run")}
        </h2>
        {c.items.length === 0 ? (
          <p className="text-sm text-muted">{t("empty")}</p>
        ) : (
          <ol className="divide-y divide-foreground/10 border-y border-foreground/15" data-testid="collection-items">
            {c.items.map((i) => (
              <li key={i.position} className="py-3">
                {i.scene ? (
                  <Link href={`${org}/matches/${i.scene.match_id}?tab=video&t=${i.scene.start_ms}`} className="font-medium underline underline-offset-4">
                    {i.scene.title || t("scene")} · {time(i.scene.start_ms)} {t("to")} {time(i.scene.end_ms)}
                  </Link>
                ) : i.play ? (
                  <Link href={`${org}/plays/${i.play.id}`} className="font-medium underline underline-offset-4">
                    {i.play.name}
                  </Link>
                ) : null}
                {i.text && <p className={i.kind === "note" ? "whitespace-pre-line" : "text-sm text-muted"}>{i.text}</p>}
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

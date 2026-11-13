import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { PresentView } from "./present-view";

/**
 * "Am Bildschirm zeigen" (SPEC 7.7, UX test B04): the collection full screen. A presentation read
 * as a collection opens its own presenter.
 */
// the tab says what is shown, not only the product (UX test B49)
export async function generateMetadata({ params }: { params: Promise<{ orgId: string; collectionId: string }> }): Promise<Metadata> {
  const { orgId, collectionId } = await params;
  const { data } = await (await serverApi()).GET("/v1/orgs/{org_id}/collections/{collection_id}", { params: { path: { org_id: orgId, collection_id: collectionId } } });
  const t = await getTranslations("collections");
  return { title: data ? `${data.title} · ${t("showTitle")}` : t("showTitle") };
}

export default async function PresentCollection({ params }: { params: Promise<{ orgId: string; collectionId: string }> }) {
  const { orgId, collectionId } = await params;
  const { data } = await (await serverApi()).GET("/v1/orgs/{org_id}/collections/{collection_id}", {
    params: { path: { org_id: orgId, collection_id: collectionId } },
  });
  if (!data) notFound();
  if (data.source === "presentation") redirect(`/app/${orgId}/presentations/${collectionId}/present`);
  return <PresentView orgId={orgId} collection={data} />;
}

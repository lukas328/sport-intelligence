import { notFound, redirect } from "next/navigation";
import { serverApi } from "@/lib/api";
import { PresentView } from "./present-view";

/**
 * "Am Bildschirm zeigen" (SPEC 7.7, UX test B04): the collection full screen. A presentation read
 * as a collection opens its own presenter.
 */
export default async function PresentCollection({ params }: { params: Promise<{ orgId: string; collectionId: string }> }) {
  const { orgId, collectionId } = await params;
  const { data } = await (await serverApi()).GET("/v1/orgs/{org_id}/collections/{collection_id}", {
    params: { path: { org_id: orgId, collection_id: collectionId } },
  });
  if (!data) notFound();
  if (data.source === "presentation") redirect(`/app/${orgId}/presentations/${collectionId}/present`);
  return <PresentView orgId={orgId} collection={data} />;
}

import { redirect } from "next/navigation";
import { serverApi } from "@/lib/api";

/**
 * "Am Bildschirm zeigen" (SPEC 7.7). A presentation read as a collection opens its presenter; the
 * full-screen view for other collections comes with the new look and opens the collection for now.
 */
export default async function PresentCollection({ params }: { params: Promise<{ orgId: string; collectionId: string }> }) {
  const { orgId, collectionId } = await params;
  const { data } = await (await serverApi()).GET("/v1/orgs/{org_id}/collections/{collection_id}", {
    params: { path: { org_id: orgId, collection_id: collectionId } },
  });
  if (data?.source === "presentation") redirect(`/app/${orgId}/presentations/${collectionId}/present`);
  redirect(`/app/${orgId}/collections/${collectionId}`);
}

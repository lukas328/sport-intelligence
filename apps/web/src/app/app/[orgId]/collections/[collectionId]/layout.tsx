import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { serverApi } from "@/lib/api";

/** An unknown collection answers 404 here, above the loading skeleton (UX test N18, review R40). */
export default async function CollectionLayout({ children, params }: { children: ReactNode; params: Promise<{ orgId: string; collectionId: string }> }) {
  const { orgId, collectionId } = await params;
  const { data } = await (await serverApi()).GET("/v1/orgs/{org_id}/collections/{collection_id}", {
    params: { path: { org_id: orgId, collection_id: collectionId } },
  });
  if (!data) notFound();
  return children;
}

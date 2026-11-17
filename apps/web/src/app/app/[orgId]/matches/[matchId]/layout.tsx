import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { serverApi } from "@/lib/api";

/**
 * An unknown match answers 404 here, above the loading skeleton: a skeleton starts the answer
 * (200) before the page could say «not found» (UX test N18, review R40). The page asks for the
 * same match again; the request is the same and served from the request's memo.
 */
export default async function MatchLayout({ children, params }: { children: ReactNode; params: Promise<{ orgId: string; matchId: string }> }) {
  const { orgId, matchId } = await params;
  const { data } = await (await serverApi()).GET("/v1/orgs/{org_id}/matches/{match_id}", {
    params: { path: { org_id: orgId, match_id: matchId } },
  });
  if (!data) notFound();
  return children;
}

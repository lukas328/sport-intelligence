import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { TeamChrome } from "@/components/shell/section-nav";
import { serverApi } from "@/lib/api";

export default async function TeamLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ orgId: string; teamId: string }>;
}) {
  const { orgId, teamId } = await params;
  const { data: team } = await (await serverApi()).GET("/v1/orgs/{org_id}/teams/{team_id}", {
    params: { path: { org_id: orgId, team_id: teamId } },
  });
  if (!team) notFound();
  return (
    <div className="space-y-8">
      <TeamChrome />
      {children}
    </div>
  );
}

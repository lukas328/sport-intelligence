"use client";

import { useShell } from "@/components/shell/context";
import { BackLink } from "@/components/ui/back-link";

/** Back from an opponent: to where the coach came from (usually the match), else the fixtures of
 * the current team. */
export function BackToFixtures({ orgId }: { orgId: string }) {
  const { team } = useShell();
  return <BackLink fallback={team ? `/app/${orgId}/teams/${team.id}/matches` : `/app/${orgId}`} />;
}

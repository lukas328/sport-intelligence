"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/client";

/** "Fürs Team zusammenstellen" (SPEC 7.1, 7.2): a draft collection from the three things. */
export function FromMatchButton({ orgId, teamId, matchId, opponent }: { orgId: string; teamId: string; matchId: string; opponent: string }) {
  const t = useTranslations("collections");
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  return (
    <Button
      variant="secondary"
      loading={busy}
      data-testid="collection-from-match"
      onClick={async () => {
        setBusy(true);
        const { data } = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/collections/from-match", {
          params: { path: { org_id: orgId, team_id: teamId } },
          body: { match_id: matchId, title: t("fromMatchTitle", { opponent }) },
        });
        setBusy(false);
        if (data) router.push(`/app/${orgId}/collections/${data.id}`);
      }}
    >
      {t("fromMatch")}
    </Button>
  );
}

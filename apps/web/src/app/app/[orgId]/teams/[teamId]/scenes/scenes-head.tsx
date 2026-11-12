"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { PageHeader } from "@/components/ui/page-header";
import { api } from "@/lib/client";

/** The Seitenkopf of Szenen: how many scenes from how many matches (the unfiltered search). */
export function ScenesHead({ orgId, teamId, matches }: { orgId: string; teamId: string; matches: number }) {
  const t = useTranslations("anlauf");
  const all = useQuery({
    queryKey: ["search-total", teamId],
    // a scene has a video time: events without one are figures, not scenes
    queryFn: async () => {
      const r = (await api.POST("/v1/orgs/{org_id}/teams/{team_id}/search", { params: { path: { org_id: orgId, team_id: teamId } }, body: { limit: 500 } })).data;
      return r ? r.hits.filter((h) => h.video_id && h.t_ms != null).length : null;
    },
  });
  return <PageHeader eyebrow={t("scenesKick", { matches })} title={all.data != null ? t("scenesTitle", { count: all.data, matches }) : " "} />;
}

"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useThingText } from "@/components/anlauf/three-things-view";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/client";
import { goalRuns, thingSequence, useMatchGraphics } from "@/lib/graphics";
import { threeThings } from "@/lib/three-things";

/**
 * "Fürs Team zusammenstellen" (SPEC 7.1, 7.2): a draft collection from the three things as the
 * app shows them: a note per thing, then exactly its scenes, each once (UX test B16).
 */
export function FromMatchButton({ orgId, teamId, matchId, opponent }: { orgId: string; teamId: string; matchId: string; opponent: string }) {
  const t = useTranslations("collections");
  const ta = useTranslations("anlauf");
  const text = useThingText();
  const router = useRouter();
  const g = useMatchGraphics(orgId, matchId);
  const [busy, setBusy] = useState(false);
  function items() {
    if (!g.data) return undefined;
    const things = threeThings(goalRuns(g.data));
    if (things.length === 0) return undefined;
    const out: { kind: "note" | "scene"; text?: string; event_id?: string }[] = [];
    things.forEach((x, i) => {
      out.push({ kind: "note", text: ta("thingTitle", { n: i + 1, thing: text(x) }) });
      for (const s of thingSequence(g.data!, i + 1, things)) out.push({ kind: "scene", event_id: s.event_id });
    });
    return out;
  }
  return (
    <Button
      variant="secondary"
      loading={busy}
      data-testid="collection-from-match"
      onClick={async () => {
        setBusy(true);
        const { data } = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/collections/from-match", {
          params: { path: { org_id: orgId, team_id: teamId } },
          body: { match_id: matchId, title: t("fromMatchTitle", { opponent }), items: items() },
        });
        setBusy(false);
        if (data) router.push(`/app/${orgId}/collections/${data.id}`);
      }}
    >
      {t("fromMatch")}
    </Button>
  );
}

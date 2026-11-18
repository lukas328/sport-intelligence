"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { useThingText } from "@/components/anlauf/three-things-view";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/client";
import { goalRuns, type MatchGraphics, thingSequence, useMatchGraphics } from "@/lib/graphics";
import { type Thing, threeThings } from "@/lib/three-things";

type Item = { kind: "note" | "scene"; text?: string; event_id?: string };

/**
 * The entries of a draft from the three things: a note per thing, then its scenes with a place in
 * the video, each once (UX test B16, A5). A goal only from the report or drawn in the example has
 * no scene to show the team and is left out.
 */
export function draftItems(g: MatchGraphics, title: (n: number, thing: Thing) => string): { items: Item[]; scenes: number } {
  const things = threeThings(goalRuns(g));
  const items: Item[] = [];
  const seen = new Set<string>();
  things.forEach((x, i) => {
    const scenes = thingSequence(g, i + 1, things).filter((s) => s.has_video && s.t_ms != null && !seen.has(s.event_id));
    if (scenes.length === 0) return;
    items.push({ kind: "note", text: title(i + 1, x) });
    for (const s of scenes) {
      seen.add(s.event_id);
      items.push({ kind: "scene", event_id: s.event_id });
    }
  });
  return { items, scenes: seen.size };
}

/**
 * "Fürs Team zusammenstellen" (SPEC 7.1, 7.2): a draft collection from the three things as the
 * app shows them. Offered only once the points are loaded and have scenes in the video, so the
 * draft never starts empty (A5).
 */
export function FromMatchButton({ orgId, teamId, matchId, opponent }: { orgId: string; teamId: string; matchId: string; opponent: string }) {
  const t = useTranslations("collections");
  const ta = useTranslations("anlauf");
  const text = useThingText();
  const router = useRouter();
  const g = useMatchGraphics(orgId, matchId);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const draft = useMemo(() => (g.data ? draftItems(g.data, (n, x) => ta("thingTitle", { n, thing: text(x) })) : null), [g.data, ta, text]);
  if (!draft || draft.scenes === 0) return null;
  return (
    <span className="inline-flex flex-wrap items-center gap-3">
      <Button
        variant="secondary"
        loading={busy}
        data-testid="collection-from-match"
        onClick={async () => {
          setBusy(true);
          setFailed(false);
          const { data } = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/collections/from-match", {
            params: { path: { org_id: orgId, team_id: teamId } },
            body: { match_id: matchId, title: t("fromMatchTitle", { opponent }), items: draft.items },
          });
          setBusy(false);
          if (data) router.push(`/app/${orgId}/collections/${data.id}`);
          else setFailed(true);
        }}
      >
        {t("fromMatch")}
      </Button>
      {failed && (
        <span role="alert" className="text-[15px] font-semibold text-error">
          {t("fromMatchFailed")}
        </span>
      )}
    </span>
  );
}

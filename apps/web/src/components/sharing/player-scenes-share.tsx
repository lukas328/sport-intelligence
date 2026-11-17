"use client";

import { Share2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/client";
import { blockedReason, type ShareOptions } from "@/lib/share/policy";
import { ShareButton } from "./share-button";

export interface PlayerScene {
  start_ms: number;
  end_ms: number;
  /** «12:30 Tor», as the coach sees it in the overview */
  title: string;
}

/**
 * «Deine Szenen» of one player as a link for the chat (K20): a collection «Szenen #7 gegen …»
 * with the player's scenes (jersey number only, no name, no coach notes), then the usual share
 * dialog. The same collection is used again on the next click.
 */
export function PlayerScenesShare({ orgId, matchId, number, scenes }: { orgId: string; matchId: string; number: number; scenes: PlayerScene[] }) {
  const t = useTranslations("share");
  const [busy, setBusy] = useState(false);
  const [target, setTarget] = useState<{ teamId: string; id: string } | null>(null);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const match = (await api.GET("/v1/orgs/{org_id}/matches/{match_id}", { params: { path: { org_id: orgId, match_id: matchId } } })).data;
      if (!match) throw new Error("match");
      const path = { org_id: orgId, team_id: match.team_id };
      const options = (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/share-options", { params: { path } })).data as ShareOptions | undefined;
      // not allowed here (youth team, role): the dialog explains it, nothing is created
      if (blockedReason(options, "collection")) {
        setTarget({ teamId: match.team_id, id: "" });
        setOpen(true);
        return;
      }
      const title = t("player.title", { number, opponent: match.opponent?.name ?? "" }).trim();
      const existing = (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/collections", { params: { path } })).data?.find((c) => c.title === title && c.source === "collection");
      let id = existing?.id;
      if (!id) {
        const created = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/collections", {
          params: { path },
          body: { title, items: scenes.map((s) => ({ kind: "scene" as const, match_id: matchId, start_ms: s.start_ms, end_ms: s.end_ms, title: s.title.trim() })) },
        });
        id = created.data?.id;
      }
      if (!id) throw new Error("collection");
      setTarget({ teamId: match.team_id, id });
      setOpen(true);
    } catch {
      setError(t("player.failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Button variant="ghost" size="sm" loading={busy} onClick={() => void start()} aria-label={t("player.aria", { number })} data-testid="player-scenes-share">
        <Share2 aria-hidden />
        <span className="max-sm:sr-only">{t("player.button")}</span>
      </Button>
      {target && <ShareButton orgId={orgId} teamId={target.teamId} kind="collection" targetId={target.id} open={open} onOpenChange={setOpen} trigger={null} />}
      {error && (
        <span role="alert" className="block text-[15px] text-error">
          {error}
        </span>
      )}
    </>
  );
}

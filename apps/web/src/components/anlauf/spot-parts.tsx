"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { DialogContent, DialogRoot, DialogTrigger } from "@/components/ui/dialog";
import { buttonClass } from "@/components/ui/button";
import { api } from "@/lib/client";
import type { MatchGraphics } from "@/lib/graphics";
import { checkMinutes, goalsWithoutSpot, type SpotAnswer, type SpotOrientation, type SpotZone, spotCounts } from "@/lib/shot-spot";
import type { Pt } from "./geometry";
import { ShotSpotPicker } from "./shot-spot-picker";

type Goal = MatchGraphics["goals"][number];

/** Saves where a goal's shot came from (PUT …/goals/{event}/spot) and refreshes the graphics. */
export function useSaveSpot(orgId: string, matchId: string) {
  const qc = useQueryClient();
  return async (eventId: string, answer: SpotAnswer, point?: Pt) => {
    const r = await api.PUT("/v1/orgs/{org_id}/matches/{match_id}/goals/{event_id}/spot", {
      params: { path: { org_id: orgId, match_id: matchId, event_id: eventId } },
      body: { shot_zone: answer, ...(point ? { x: point[0], y: point[1] } : {}) },
    });
    if (r.error || !r.response.ok) {
      const p = r.error as { detail?: string; title?: string } | undefined;
      throw new Error(p?.detail || p?.title || String(r.response.status));
    }
    await qc.invalidateQueries({ queryKey: ["graphics", matchId] });
    return r.data ?? null;
  };
}

/**
 * How the small court of «Von wo?» lies for a goal: as the camera sees it (the attacked goal left
 * or right as in the video) when the API knows it, else with the goal at the top. `ready` is false
 * while it is asked, so the court does not turn under the coach's thumb.
 */
export function useGoalView(orgId: string, matchId: string, eventId: string | null): { orientation: SpotOrientation; ready: boolean } {
  const q = useQuery({
    queryKey: ["goal-view", matchId, eventId],
    enabled: eventId != null,
    staleTime: 300_000,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/goals/{event_id}/view", { params: { path: { org_id: orgId, match_id: matchId, event_id: eventId! } } })).data ?? null,
  });
  return { orientation: q.data?.goal_in_video ?? "top", ready: eventId == null || !q.isLoading };
}

/** The place of a goal in words: «Rückraum links», «… , geschätzt», or «Wurfort fehlt». */
export function useSpotText() {
  const t = useTranslations("spot");
  // «Weiss nicht» with an estimate behind it reads «…, geschätzt» too: only the coach's place is plain (V1)
  return (g: { zone?: string | null; spot_by_coach?: boolean }) =>
    g.zone ? t(g.spot_by_coach ? "of" : "ofEstimated", { zone: t(`zone.${g.zone}` as "zone.la") }) : t("missing");
}

/**
 * The place of one goal with «Wurfort ändern» (or «eintragen»): two taps, the button and the new
 * place, in the scene list and beside the tactics camera (fourth real-video test H7).
 */
export function SpotChange({ orgId, matchId, goal, label }: { orgId: string; matchId: string; goal: Goal; label: string }) {
  const t = useTranslations("spot");
  const save = useSaveSpot(orgId, matchId);
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const zone = goal.zone as SpotZone | null;
  const view = useGoalView(orgId, matchId, open ? goal.event_id : null);
  return (
    <DialogRoot open={open} onOpenChange={(v) => (setOpen(v), setFailed(null))}>
      <DialogTrigger className="min-h-11 cursor-pointer border-0 bg-transparent p-0 text-[15px] font-bold text-ink underline decoration-[1.5px] underline-offset-4" data-testid="spot-change">
        {goal.zone ? t("change") : t("set")}
      </DialogTrigger>
      <DialogContent title={t("dialogTitle")} description={label}>
        <ShotSpotPicker
          disabled={busy || !view.ready}
          orientation={view.orientation}
          // an estimate is never marked (V2); the coach's own earlier answer reads «Bisher»
          current={zone && goal.spot_by_coach ? zone : null}
          onPick={(answer, point) => {
            setBusy(true);
            setFailed(null);
            save(goal.event_id, answer, point)
              .then(() => setOpen(false))
              .catch((e: unknown) => setFailed(e instanceof Error ? e.message : String(e)))
              .finally(() => setBusy(false));
          }}
        />
        {failed && (
          <p role="alert" className="mt-3 border-l-4 border-loss pl-3 text-[15px] font-semibold">
            {failed}
          </p>
        )}
      </DialogContent>
    </DialogRoot>
  );
}

/**
 * Where the three things stand (fourth real-video test H7): how many goals have a place, what is
 * missing, and the way to fill it in. Never a sentence without a way: with places missing the key
 * «In einer Minute nachtragen»; with all places in and no pattern, the rule.
 */
export function SpotStatus({ orgId, matchId, graphics, things, compact }: { orgId: string; matchId: string; graphics: MatchGraphics; things: number; compact?: boolean }) {
  const t = useTranslations("spot");
  const c = spotCounts(graphics);
  if (c.total === 0) return null;
  if (compact && c.missing === 0) return null;
  const href = `/app/${orgId}/matches/${matchId}/check?spots=1`;
  return (
    <section className={compact ? "mt-4 max-w-[62ch] space-y-2" : "max-w-[62ch] space-y-3"} data-testid="spot-status">
      <p className="m-0 text-[17px]">
        {things > 0 && things < 3 && <b className="mr-1">{t("soFar", { n: things })}</b>}
        {t("status", { placed: c.placed, total: c.total })} {c.missing > 0 ? t("missingLine", { n: c.missing }) : things === 0 ? `${t("noPattern")} ${t("rule")}` : ""}
      </p>
      {!compact && c.missing > 0 && <p className="m-0 text-[15px] text-ink-2">{t("rule")}</p>}
      {c.missing > 0 && (
        <Link href={href} className={compact ? "inline-flex min-h-11 items-center font-bold text-ink underline underline-offset-4" : buttonClass("primary")} data-testid="spot-fill">
          {t("fill", { minutes: checkMinutes(0, 0, goalsWithoutSpot(graphics).length) })}
        </Link>
      )}
    </section>
  );
}

/** Under the scene of a goal (a thing's scene, Punkt 1): its place and «Wurfort ändern» (V4). */
export function SceneSpot({ orgId, matchId, graphics, eventId, label }: { orgId: string; matchId: string; graphics: MatchGraphics; eventId: string; label: string }) {
  const text = useSpotText();
  const goal = graphics.goals.find((x) => x.event_id === eventId);
  if (!goal) return null;
  return (
    <p className="m-0 mt-1.5 flex flex-wrap items-center gap-x-3 text-[15px]" data-testid="scene-spot">
      <span className="text-ink-2">{text(goal)}</span>
      <SpotChange orgId={orgId} matchId={matchId} goal={goal} label={label} />
    </p>
  );
}

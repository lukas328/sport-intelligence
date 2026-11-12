"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { CameraKey, SectionHead } from "@/components/anlauf/blocks";
import { Rail } from "@/components/anlauf/charts";
import { clockOf, SceneCamera } from "@/components/anlauf/three-things-view";
import { ShareButton } from "@/components/sharing/share-button";
import { Button } from "@/components/ui/button";
import { VideoPlayer, type PlayerHandle } from "@/components/video/player";
import { api } from "@/lib/client";
import { goalRuns, reportGoals, type MatchGraphics } from "@/lib/graphics";
import { threeThings } from "@/lib/three-things";
import { cn } from "@/lib/utils";

type Match = Schemas["MatchOut"];
type Video = Schemas["VideoOut"];

const PHASE = 3; // minutes around the scene: the phase on the right and on the Rail
const BEFORE = 6000; // a scene starts 6 s before its goal

/**
 * The tab Video (SPEC 7.3): one stage that switches between the video and the tactics camera,
 * the Ball-Linie and the legend, the Rail with the marked phase, the scenes of the phase and the
 * notes at the side, four actions. The workbench (events, defence systems, comments, feedback)
 * sits behind «Mehr» (onBench); what is a check (court, throw-off, goals, persons) is Prüfen.
 */
export function VideoStage({
  orgId,
  match,
  video,
  graphics,
  oppName,
  staff,
  onBench,
}: {
  orgId: string;
  match: Match;
  video: Video;
  graphics: MatchGraphics;
  oppName: string;
  staff: boolean;
  onBench: () => void;
}) {
  const t = useTranslations("anlauf");
  const goals = graphics.goals.filter((g) => g.has_video || g.source === "demo");
  // the stage opens on the first goal of Punkt 1 (SPEC 7.3: the scene and its thing)
  const first = threeThings(goalRuns(graphics))[0]?.goals.find((g) => g.eventId)?.eventId;
  const [eventId, setEventId] = useState<string | null>(first ?? goals[0]?.event_id ?? null);
  const goal = goals.find((g) => g.event_id === eventId) ?? null;
  // Taktik is the default once the court is confirmed (SPEC 7.3)
  const [mode, setMode] = useState<"video" | "taktik">(graphics.field_confirmed ? "taktik" : "video");
  const player = useRef<PlayerHandle>(null);
  const [kept, setKept] = useState<string | null>(null);
  const minute = goal?.minute ?? 0;
  const phase: [number, number] = [Math.max(0, Math.floor(minute - PHASE)), Math.min(60, Math.ceil(minute + PHASE))];
  const inPhase = goals.filter((g) => g.minute != null && g.minute >= phase[0] && g.minute <= phase[1]);
  const label = (g: (typeof goals)[number]) => t("goalOf", { team: g.team === "opp" ? oppName : t("us"), clock: clockOf(g.minute) });
  const notes = useQuery({
    queryKey: ["comments", match.id],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/comments", { params: { path: { org_id: orgId, match_id: match.id } } })).data ?? [],
  });
  const near = (notes.data ?? []).filter((c) => goal?.t_ms != null && c.t_ms != null && Math.abs(c.t_ms - goal.t_ms) < PHASE * 60_000).slice(0, 3);

  // the video follows the chosen scene
  useEffect(() => {
    if (mode === "video" && goal?.t_ms != null) player.current?.seek(Math.max(0, goal.t_ms - BEFORE));
  }, [mode, goal?.t_ms]);

  async function keep() {
    if (goal?.t_ms == null) return;
    const r = await api.POST("/v1/orgs/{org_id}/clips", {
      params: { path: { org_id: orgId } },
      body: { match_id: match.id, start_ms: Math.max(0, goal.t_ms - BEFORE), end_ms: goal.t_ms + 2000, title: label(goal) },
    });
    if (r.response.ok) setKept(goal.event_id);
  }

  const toggle = (
    <span className="flex border-[1.5px] border-[#4a5058]" role="group" aria-label={t("stageMode")}>
      {(["video", "taktik"] as const).map((m) => (
        <button
          key={m}
          type="button"
          aria-pressed={mode === m}
          onClick={() => setMode(m)}
          className={cn("min-h-11 cursor-pointer border-0 px-3 font-sans text-[13px] font-bold", mode === m ? "bg-[#e9eef2] text-court-bar" : "bg-transparent text-[#a8b1ba]")}
        >
          {t(m === "video" ? "modeVideo" : "modeTaktik")}
        </button>
      ))}
    </span>
  );
  const media = `/v1/orgs/${orgId}/videos/${video.id}/media`;

  return (
    <section className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_340px]" aria-label={t("cameraTitle")} data-testid="video-stage">
      <div className="min-w-0">
        <div hidden={mode !== "video"}>
          <VideoPlayer ref={player} src={`${media}/hls/master.m3u8`} poster={video.has_poster ? `${media}/poster.jpg` : undefined} fps={video.fps} />
          <div className="flex flex-wrap items-center gap-2.5 bg-court-bar px-3 py-2 font-mono text-[13px] font-semibold text-court-text">
            {toggle}
            {goal && <span className="ml-auto font-mono text-xl text-white">{clockOf(goal.minute)}</span>}
          </div>
        </div>
        {mode === "taktik" && eventId && goal && (
          <SceneCamera
            key={eventId}
            orgId={orgId}
            matchId={match.id}
            eventId={eventId}
            label={label(goal)}
            view="camL"
            width={900}
            caption={label(goal)}
            captionSmall={t("positionsFromVideo")}
            barExtra={toggle}
          />
        )}
        <CameraKey us={t("us")} them={oppName} referee={t("referee")} ball={t("ball")} />
        <p className="mt-1 text-[13px] text-ink-2">{t("numberRead")}</p>
        {graphics.report_goals.length > 0 && (
          <div className="mt-6">
            <Rail goals={reportGoals(graphics)} phase={phase} at={goal?.minute ?? null} label={t("rail")} />
            <p className="mt-1 flex justify-between text-[13px] text-ink-2">
              <span>{t("throwOff")}</span>
              <span>{t("halfTimeWord")}</span>
              <span>{t("fullTime")}</span>
            </p>
          </div>
        )}
        <div className="mt-6 flex flex-wrap gap-3">
          <Button onClick={() => void keep()} disabled={goal?.t_ms == null || kept === goal?.event_id}>
            {kept === goal?.event_id ? t("kept") : t("keepScene")}
          </Button>
          {staff && (
            <>
              <Button variant="secondary" onClick={onBench}>
                {t("draw")}
              </Button>
              <Button variant="secondary" onClick={onBench}>
                {t("highlight")}
              </Button>
              <ShareButton orgId={orgId} teamId={match.team_id} kind="match" targetId={match.id} />
            </>
          )}
        </div>
      </div>
      <aside className="min-w-0">
        <SectionHead title={t("phaseTitle", { from: phase[0], to: phase[1] })} note={t("scenes", { count: inPhase.length })} />
        <ul className="m-0 list-none p-0">
          {inPhase.map((g) => {
            const on = g.event_id === eventId;
            return (
              <li key={g.event_id}>
                <button
                  type="button"
                  aria-pressed={on}
                  onClick={() => setEventId(g.event_id)}
                  className={cn("grid min-h-11 w-full cursor-pointer grid-cols-[58px_minmax(0,1fr)] gap-2.5 border-t border-rule px-3 py-2.5 text-left", on ? "bg-attn text-attn-ink" : "bg-transparent text-ink hover:bg-ink/5")}
                >
                  <b className="font-num text-[17px]">{clockOf(g.minute)}</b>
                  <span className="text-[15px] leading-snug">
                    {label(g)}
                    <small className={cn("block text-[13px]", on ? "text-attn-ink" : "text-ink-2")}>{on ? t("running") : g.zone ? t(`zoneShort.${g.zone}` as "zoneShort.la") : ""}</small>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
        <div className="mt-10">
          <SectionHead as="h3" title={t("notes")} />
          {near.length > 0 ? (
            near.map((c) => (
              <p key={c.id} className="mb-3 border-l-4 border-club pl-3 text-[17px] italic">
                {c.t_ms != null && `${formatMs(c.t_ms)} `}
                {c.body}
              </p>
            ))
          ) : (
            <p className="text-[15px] text-ink-2">{t("noNotes")}</p>
          )}
          {staff && (
            <button type="button" onClick={onBench} className="mt-1 min-h-11 cursor-pointer font-bold underline decoration-[1.5px] underline-offset-4">
              {t("writeNote")}
            </button>
          )}
        </div>
        <p className="mt-8">
          <button type="button" onClick={onBench} className="min-h-11 cursor-pointer font-bold underline decoration-[1.5px] underline-offset-4" data-testid="bench-open">
            {t("more")}
          </button>
        </p>
        <details className="mt-6">
          <summary className="min-h-11 cursor-pointer content-center font-bold underline decoration-[1.5px] underline-offset-4">
            {t("sceneList")} ({goals.length})
          </summary>
          <ul className="m-0 mt-2 max-h-[420px] list-none overflow-y-auto p-0">
            {goals.map((g) => (
              <li key={g.event_id}>
                <button type="button" onClick={() => setEventId(g.event_id)} className="flex min-h-11 w-full cursor-pointer items-center gap-3 border-t border-rule bg-transparent px-1 text-left text-[15px] text-ink hover:bg-ink/5" aria-pressed={g.event_id === eventId}>
                  <b className="font-num w-12">{clockOf(g.minute)}</b>
                  {label(g)}
                </button>
              </li>
            ))}
          </ul>
        </details>
      </aside>
    </section>
  );
}

function formatMs(ms: number): string {
  const s = Math.round(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

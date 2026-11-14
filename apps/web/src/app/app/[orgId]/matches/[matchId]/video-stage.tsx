"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { usePhone } from "@/lib/use-phone";
import { CameraKey, SectionHead } from "@/components/anlauf/blocks";
import { Rail } from "@/components/anlauf/charts";
import { clockOf, SceneCamera, useThingText } from "@/components/anlauf/three-things-view";
import { Button } from "@/components/ui/button";
import { VideoPlayer, type PlayerHandle } from "@/components/video/player";
import { api } from "@/lib/client";
import { goalRuns, reportGoals, thingSequence, type MatchGraphics } from "@/lib/graphics";
import { threeThings } from "@/lib/three-things";
import { cn } from "@/lib/utils";
import { usePartMarkers } from "./parts-panel";

type Match = Schemas["MatchOut"];
type Video = Schemas["VideoOut"];
type Goal = MatchGraphics["goals"][number];

const mmss = (ms: number) => `${Math.floor(ms / 60000)}:${String(Math.floor((ms % 60000) / 1000)).padStart(2, "0")}`;
const PHASE = 3; // minutes around the scene: the phase on the right and on the Rail
const BEFORE = 8000; // a scene starts 8 s before its goal, as on the tactics camera (G3)
const AFTER = 2000;

/**
 * The tab Video (SPEC 7.3): one stage that switches between the video and the tactics camera,
 * the Ball-Linie and the legend, the Rail with the marked phase, the scenes at the side, the
 * actions. With `thing` (?thing=n) the side holds exactly the scenes of that thing, one after
 * the other («Nächste Szene», «Alle abspielen»); without it the scenes of the phase around the
 * chosen goal. The workbench sits behind «Mehr» (onBench); checks are in Prüfen.
 */
export function VideoStage({
  orgId,
  match,
  video,
  graphics,
  ownName,
  oppName,
  staff,
  thing,
  scene = null,
  onThing,
  onBench,
}: {
  orgId: string;
  match: Match;
  video: Video;
  graphics: MatchGraphics;
  ownName: string;
  oppName: string;
  staff: boolean;
  thing: number | null;
  /** a goal's scene to open at (?scene=eventId, from «Szene zeigen» in the Spiel tab) */
  scene?: string | null;
  onThing: (n: number | null) => void;
  onBench: () => void;
}) {
  const t = useTranslations("anlauf");
  const tz = useTranslations("seasonPage");
  const text = useThingText();
  const partMarkers = usePartMarkers(match.videos);
  const goals = graphics.goals.filter((g) => g.has_video || g.source === "demo");
  const things = threeThings(goalRuns(graphics));
  const chosen = thing != null ? (things[thing - 1] ?? null) : null;
  // the scenes of the thing, in the order of the match, each a goal with a video time
  const sequence: Goal[] = chosen ? thingSequence(graphics, thing!, things) : [];
  const asked = scene && goals.some((g) => g.event_id === scene) ? scene : null;
  const first = asked ?? sequence[0]?.event_id ?? things[0]?.goals.find((g) => g.eventId)?.eventId ?? goals[0]?.event_id ?? null;
  const [eventId, setEventId] = useState<string | null>(first);
  // a new thing starts at its first scene
  useEffect(() => {
    if (sequence[0]) setEventId(sequence[0].event_id);
    setAll(false);
  }, [thing]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (asked) setEventId(asked);
  }, [asked]);
  const goal = goals.find((g) => g.event_id === eventId) ?? null;
  // Taktik is the default once the court is confirmed (SPEC 7.3)
  const [mode, setMode] = useState<"video" | "taktik">(graphics.field_confirmed ? "taktik" : "video");
  // on a phone the attacked half fills the width, numbers stay readable (UX test B51)
  const phone = usePhone();
  const [all, setAll] = useState(false);
  const player = useRef<PlayerHandle>(null);
  const [kept, setKept] = useState<string | null>(null);
  const minute = goal?.minute ?? 0;
  // the minutes the video covers (span): a short video is one phase with all its goals, the Rail
  // runs over these minutes, not over 60 (real-video test, second round)
  const span = graphics.span ?? null;
  const short = span ? span[1] - span[0] <= 2 * PHASE + 2 : goals.every((g) => g.minute == null);
  const phase: [number, number] =
    short && span ? [Math.floor(span[0]), Math.ceil(span[1])] : [Math.max(span ? Math.floor(span[0]) : 0, Math.floor(minute - PHASE)), Math.min(span ? Math.ceil(span[1]) : 60, Math.ceil(minute + PHASE))];
  const inPhase = short ? goals : goals.filter((g) => g.minute != null && g.minute >= phase[0] && g.minute <= phase[1]);
  // one row per goal (G8: rows came twice without a throw-off)
  const list = [...new Map((chosen ? sequence : inPhase).map((g) => [g.event_id, g])).values()];
  const at = list.findIndex((g) => g.event_id === eventId);
  const team = (g: Goal) => (g.team === "opp" ? oppName : ownName);
  // without the throw-off the place in the video stands for the clock (G8)
  const when = (g: Goal) => (g.minute != null ? clockOf(g.minute) : g.t_ms != null ? t("atVideo", { time: mmss(g.t_ms) }) : "");
  const label = (g: Goal) => t("goalOf", { team: team(g), clock: when(g) });
  const where = (g: Goal) => (!g.zone ? "" : ["la", "ra", "rl", "rm", "rr", "kr"].includes(g.zone) ? tz(`zoneTitle.${g.zone}` as "zoneTitle.ra") : t(`zoneShort.${g.zone}` as "zoneShort.gs"));
  const notes = useQuery({
    queryKey: ["comments", match.id],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/comments", { params: { path: { org_id: orgId, match_id: match.id } } })).data ?? [],
  });
  const near = (notes.data ?? []).filter((c) => goal?.t_ms != null && c.t_ms != null && Math.abs(c.t_ms - goal.t_ms) < PHASE * 60_000).slice(0, 3);

  const step = (d: 1 | -1) => {
    const next = list[at + d];
    if (next) setEventId(next.event_id);
    else if (d === 1) setAll(false);
  };

  async function keep() {
    if (goal?.t_ms == null) return;
    const r = await api.POST("/v1/orgs/{org_id}/clips", {
      params: { path: { org_id: orgId } },
      body: { match_id: match.id, start_ms: Math.max(0, goal.t_ms - BEFORE), end_ms: goal.t_ms + AFTER, title: label(goal) },
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
          className={cn("min-h-11 cursor-pointer border-0 px-3 font-sans text-[15px] font-bold", mode === m ? "bg-[#e9eef2] text-court-bar" : "bg-transparent text-[#a8b1ba]")}
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
          {goal?.t_ms != null ? (
            // one scene at a time: the window of the goal; «Alle abspielen» goes on by itself
            <VideoPlayer
              ref={player}
              key={`${goal.event_id}-${all}`}
              src={`${media}/hls/master.m3u8`}
              poster={video.has_poster ? `${media}/poster.jpg` : undefined}
              fps={video.fps}
              window={{ start_ms: Math.max(0, goal.t_ms - BEFORE), end_ms: goal.t_ms + AFTER }}
              onWindowEnd={() => (all ? step(1) : undefined)}
              autoPlay={all}
            />
          ) : (
            <VideoPlayer ref={player} src={`${media}/hls/master.m3u8`} poster={video.has_poster ? `${media}/poster.jpg` : undefined} fps={video.fps} markers={partMarkers} />
          )}
          <div className="flex flex-wrap items-center gap-2.5 bg-court-bar px-3 py-2 font-mono text-[13px] font-semibold text-court-text">
            {toggle}
            {chosen && at >= 0 && <span>{t("sceneOf", { n: at + 1, total: list.length })}</span>}
            {goal && <span className="ml-auto font-mono text-xl text-white">{when(goal)}</span>}
          </div>
        </div>
        {mode === "taktik" && eventId && goal && (
          <SceneCamera
            key={eventId}
            orgId={orgId}
            matchId={match.id}
            eventId={eventId}
            label={label(goal)}
            view={phone ? "halfB" : "camL"}
            width={phone ? 390 : 900}
            caption={chosen && at >= 0 ? `${label(goal)} · ${t("sceneOf", { n: at + 1, total: list.length })}` : label(goal)}
            captionSmall={t("positionsFromVideo")}
            barExtra={toggle}
          />
        )}
        <CameraKey us={ownName} them={oppName} referee={t("referee")} ball={t("ball")} />
        {/* no throw-off: the Rail over the video's own time, the goals at their place in it (G8) */}
        {!span && goals.length > 0 && goals.every((g) => g.minute == null) && video.duration_s ? (
          <div className="mt-6">
            <Rail
              goals={goals.filter((g) => g.t_ms != null).map((g) => ({ minute: g.t_ms! / 60_000, team: g.team === "opp" ? "opp" : "own" }))}
              at={goal?.t_ms != null ? goal.t_ms / 60_000 : null}
              length={Math.max(1, video.duration_s / 60)}
              label={t("rail")}
            />
            <p className="mt-1 flex justify-between text-[15px] text-ink-2" data-testid="rail-video">
              <span>{t("atVideo", { time: "0:00" })}</span>
              <span>{t("atVideo", { time: mmss(video.duration_s * 1000) })}</span>
            </p>
          </div>
        ) : graphics.report_goals.length > 0 && (
          <div className="mt-6">
            {span ? (
              <>
                <Rail goals={reportGoals(graphics)} phase={short ? null : phase} at={goal?.minute ?? null} from={span[0]} length={Math.max(1, span[1] - span[0])} label={t("rail")} />
                <p className="mt-1 flex justify-between text-[15px] text-ink-2" data-testid="rail-span">
                  <span>{t("minuteAt", { n: Math.floor(span[0]) })}</span>
                  <span>{t("minuteAt", { n: Math.ceil(span[1]) })}</span>
                </p>
              </>
            ) : (
              <>
                <Rail goals={reportGoals(graphics)} phase={phase} at={goal?.minute ?? null} label={t("rail")} />
                <p className="mt-1 flex justify-between text-[15px] text-ink-2">
                  <span>{t("throwOff")}</span>
                  <span>{t("halfTimeWord")}</span>
                  <span>{t("fullTime")}</span>
                </p>
              </>
            )}
          </div>
        )}
        <div className="mt-6 flex flex-wrap gap-3" data-testid="stage-actions">
          {chosen && (
            <>
              <Button onClick={() => step(1)} disabled={at >= list.length - 1} data-testid="next-scene">
                {t("nextScene")}
              </Button>
              <Button variant="secondary" onClick={() => step(-1)} disabled={at <= 0}>
                {t("prevScene")}
              </Button>
              <Button variant="secondary" aria-pressed={all} onClick={() => (setMode("video"), setAll((x) => !x))} data-testid="play-all">
                {all ? t("stopAll") : t("playAll", { n: list.length })}
              </Button>
            </>
          )}
          <Button variant={chosen ? "secondary" : "primary"} onClick={() => void keep()} disabled={goal?.t_ms == null || kept === goal?.event_id}>
            {kept === goal?.event_id ? t("kept") : t("keepScene")}
          </Button>
          {staff && (
            <Button variant="secondary" onClick={onBench}>
              {t("draw")}
            </Button>
          )}
        </div>
      </div>
      <aside className="min-w-0">
        {chosen ? (
          <SectionHead
            title={t("thingTitle", { n: thing!, thing: text(chosen) })}
            note={t("scenes", { count: list.length })}
            action={
              <button type="button" onClick={() => onThing(null)} className="min-h-11 cursor-pointer font-bold underline decoration-[1.5px] underline-offset-4">
                {t("allGoalsShort")}
              </button>
            }
          />
        ) : (
          <SectionHead title={short && !span ? t("scoreFromVideo") : t("phaseTitle", { from: phase[0], to: phase[1] })} note={t("scenes", { count: list.length })} />
        )}
        <ol className="m-0 list-none p-0" data-testid="stage-scenes">
          {list.map((g, i) => {
            const on = g.event_id === eventId;
            return (
              <li key={g.event_id}>
                <button
                  type="button"
                  aria-pressed={on}
                  onClick={() => setEventId(g.event_id)}
                  className={cn("grid min-h-11 w-full cursor-pointer grid-cols-[28px_52px_minmax(0,1fr)] gap-2 border-t border-rule px-3 py-2.5 text-left", on ? "bg-attn text-attn-ink" : "bg-transparent text-ink hover:bg-ink/5")}
                >
                  <b className="font-num text-[17px]">{chosen ? i + 1 : ""}</b>
                  <b className="font-num text-[17px]">{when(g)}</b>
                  <span className="text-[15px] leading-snug">
                    {label(g)}
                    <small className={cn("block text-[15px]", on ? "text-attn-ink" : "text-ink-2")}>{on ? t("running") : where(g)}</small>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
        {!chosen && things.length > 0 && (
          <div className="mt-6">
            <SectionHead as="h3" title={t("thingsHere")} />
            <ul className="m-0 list-none p-0">
              {things.map((x, i) => (
                <li key={x.key}>
                  <button type="button" onClick={() => onThing(i + 1)} className="flex min-h-11 w-full cursor-pointer items-baseline gap-3 border-t border-rule bg-transparent px-1 py-2 text-left text-[15px] text-ink hover:bg-ink/5">
                    <b className="font-num">{i + 1}</b>
                    <span className="min-w-0 flex-1">{text(x)}</span>
                    <span className="text-[15px] text-ink-2">{t("scenes", { count: x.goals.length })}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="mt-10">
          <SectionHead as="h3" title={t("notes")} />
          {near.length > 0 ? (
            near.map((c) => (
              <p key={c.id} className="mb-3 border-l-4 border-club-text pl-3 text-[17px] italic">
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
                <button type="button" onClick={() => (onThing(null), setEventId(g.event_id))} className="flex min-h-11 w-full cursor-pointer items-center gap-3 border-t border-rule bg-transparent px-1 text-left text-[15px] text-ink hover:bg-ink/5" aria-pressed={g.event_id === eventId}>
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

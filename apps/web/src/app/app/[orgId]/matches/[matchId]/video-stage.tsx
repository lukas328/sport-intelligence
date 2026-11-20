"use client";

import Link from "next/link";
import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { Check, SkipBack, SkipForward } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { usePhone } from "@/lib/use-phone";
import { CameraKey, SectionHead } from "@/components/anlauf/blocks";
import { Rail } from "@/components/anlauf/charts";
import { useMatchSides } from "@/components/domain/match-sides";
import { clockOf, SceneCamera, useThingText } from "@/components/anlauf/three-things-view";
import { Button } from "@/components/ui/button";
import { VideoPlayer, type PlayerHandle } from "@/components/video/player";
import { api } from "@/lib/client";
import { oppFirst } from "@/lib/match-sides";
import { cameraScene, goalRuns, reportGoals, thingSequence, useSceneCamera, type MatchGraphics } from "@/lib/graphics";
import { threeThings } from "@/lib/three-things";
import { SpotChange, useSpotText } from "@/components/anlauf/spot-parts";
import { cn } from "@/lib/utils";
import { usePartMarkers } from "./parts-panel";
import { readStageMode, STAGE_MODE_KEY, type StageMode } from "./stage-mode";

type Match = Schemas["MatchOut"];
type Video = Schemas["VideoOut"];
type Goal = MatchGraphics["goals"][number];

const mmss = (ms: number) => `${Math.floor(ms / 60000)}:${String(Math.floor((ms % 60000) / 1000)).padStart(2, "0")}`;
const PHASE = 3; // minutes around the scene: the phase on the right and on the Rail
const BEFORE = 8000; // a scene starts 8 s before its goal, as on the tactics camera (G3)
const AFTER = 2000;
/** The goal's scene: from the API (a goal from a goal candidate starts 12 s before, V6), else 8 s / 2 s. */
const sceneOf = (g: { t_ms?: number | null; scene?: [number, number] | null }) =>
  g.scene ? { start_ms: g.scene[0], end_ms: g.scene[1] } : { start_ms: Math.max(0, (g.t_ms ?? 0) - BEFORE), end_ms: (g.t_ms ?? 0) + AFTER };

/**
 * The tab Video (SPEC 7.3): one stage that switches between the video and the tactics camera,
 * the Rail with the marked phase, the scenes at the side, the actions. With `thing` (?thing=n)
 * the side holds exactly the scenes of that thing, one after the other («Nächste Szene», «Alle
 * abspielen»); without it the scenes of the phase around the chosen goal. The workbench sits
 * behind «Mehr» (onBench); checks are in Prüfen.
 *
 * App review 19.11. (UX-01 to 04, UI-05, UI-06, A11Y-01): the video is the default, the switch
 * sits above the picture and is remembered; «Feld von oben» is offered only where the scene has
 * positions, otherwise it says why. The player stays in view (sticky) while the list scrolls;
 * scenes step with buttons and the keys N and P; the end of a clip is said, with the way on.
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
  onDraw,
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
  /** «Zeichnen»: the workbench draws on this moment of the video (app review BUG-13) */
  onDraw?: (ms: number) => void;
}) {
  const t = useTranslations("anlauf");
  // the home team above the line, also in an observed match (UI check 20.11.)
  const railOppFirst = oppFirst(useMatchSides());
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
  // the video first (app review UX-01); the coach's last choice is kept on this device
  const [wanted, setWanted] = useState<StageMode>("video");
  useEffect(() => setWanted(readStageMode()), []);
  const choose = (m: StageMode) => {
    setWanted(m);
    try {
      window.localStorage.setItem(STAGE_MODE_KEY, m);
    } catch {
      // private mode or blocked storage: the choice holds for this visit only
    }
  };
  // «Feld von oben» only where the scene has positions; otherwise the switch says why
  const camera = useSceneCamera(orgId, match.id, eventId);
  const hasCamera = camera.data != null && cameraScene(camera.data, null) != null;
  const fieldOpen = camera.data != null && camera.data.field_confirmed === false;
  const mode: StageMode = wanted === "taktik" && hasCamera ? "taktik" : "video";
  // on a phone the attacked half fills the width, numbers stay readable (UX test B51)
  const phone = usePhone();
  const [all, setAll] = useState(false);
  const player = useRef<PlayerHandle>(null);
  const stageTop = useRef<HTMLDivElement>(null);
  // the scenes saved here, by goal: a second press takes the scene out again (BUG-21)
  const [kept, setKept] = useState<Record<string, string>>({});
  // the end of a scene's clip: said, with the way on (UX-04); «Weiterlaufen lassen» lifts the window
  const [ended, setEnded] = useState(false);
  const [free, setFree] = useState(false);
  useEffect(() => {
    setEnded(false);
    setFree(false);
  }, [eventId]);
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
  const spotText = useSpotText();
  const where = (g: Goal) => (!g.zone ? "" : ["la", "ra", "rl", "rm", "rr", "kr"].includes(g.zone) ? tz(`zoneTitle.${g.zone}` as "zoneTitle.ra") : t(`zoneShort.${g.zone}` as "zoneShort.gs"));
  const notes = useQuery({
    queryKey: ["comments", match.id],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/comments", { params: { path: { org_id: orgId, match_id: match.id } } })).data ?? [],
  });
  const near = (notes.data ?? []).filter((c) => goal?.t_ms != null && c.t_ms != null && Math.abs(c.t_ms - goal.t_ms) < PHASE * 60_000).slice(0, 3);

  // a scene chosen further down the page: the player comes into view (UX-02)
  const pick = (id: string) => {
    setEventId(id);
    const box = stageTop.current?.getBoundingClientRect();
    if (!box || (box.top >= 0 && box.top < window.innerHeight / 2)) return;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    stageTop.current?.scrollIntoView({ block: "start", behavior: still ? "auto" : "smooth" });
  };
  const step = (d: 1 | -1) => {
    const next = list[at + d];
    if (next) setEventId(next.event_id);
    else if (d === 1) setAll(false);
  };
  // N and P step through the scenes while the player has the focus (UX-03)
  const onKey = (key: string) => {
    if (key === "n" || key === "N") return step(1), true;
    if (key === "p" || key === "P") return step(-1), true;
    return false;
  };

  async function keep() {
    if (goal?.t_ms == null) return;
    const id = kept[goal.event_id];
    if (id) {
      const r = await api.DELETE("/v1/orgs/{org_id}/clips/{clip_id}", { params: { path: { org_id: orgId, clip_id: id } } });
      if (r.response.ok) setKept((k) => Object.fromEntries(Object.entries(k).filter(([e]) => e !== goal.event_id)));
      return;
    }
    const r = await api.POST("/v1/orgs/{org_id}/clips", {
      params: { path: { org_id: orgId } },
      body: { match_id: match.id, ...sceneOf(goal), title: label(goal) },
    });
    if (r.response.ok && r.data) setKept((k) => ({ ...k, [goal.event_id]: r.data.id }));
  }
  const isKept = goal != null && kept[goal.event_id] != null;

  const why = !hasCamera && !camera.isLoading && eventId ? (fieldOpen ? t("fieldHint") : t("noCamera")) : null;
  const toggle = (
    <span className="flex border-[1.5px] border-[#4a5058]" role="group" aria-label={t("stageMode")}>
      {(["video", "taktik"] as const).map((m) => (
        <button
          key={m}
          type="button"
          aria-pressed={mode === m}
          disabled={m === "taktik" && !hasCamera}
          aria-describedby={m === "taktik" && why ? "stage-mode-why" : undefined}
          title={m === "taktik" && why ? why : undefined}
          onClick={() => choose(m)}
          className={cn(
            "min-h-11 cursor-pointer border-0 px-3 font-sans text-[15px] font-bold disabled:cursor-not-allowed disabled:opacity-50",
            mode === m ? "bg-[#e9eef2] text-court-bar" : "bg-transparent text-[#a8b1ba]",
          )}
          data-testid={`stage-mode-${m}`}
        >
          {t(m === "video" ? "modeVideo" : "modeTaktik")}
        </button>
      ))}
    </span>
  );
  const media = `/v1/orgs/${orgId}/videos/${video.id}/media`;

  return (
    <section className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_340px]" aria-label={t("cameraTitle")} data-testid="video-stage">
      {/* phones: the column dissolves into the grid, so the player stays on top while the list
          below it scrolls; from laptops up it stays beside the list (UX-02) */}
      <div className="min-w-0 max-lg:contents">
        <div
          ref={stageTop}
          className={cn("scroll-mt-16 bg-ground", mode === "video" && "sticky top-14 z-20 lg:top-4")}
          data-testid="stage-player"
        >
          {/* the switch above the picture (UX-01) */}
          <div className="flex flex-wrap items-center gap-2.5 bg-court-bar px-3 py-2 font-mono text-[13px] font-semibold text-court-text">
            {toggle}
            {list.length > 1 && at >= 0 && <span>{t("sceneOf", { n: at + 1, total: list.length })}</span>}
            {goal && <span className="ml-auto text-xl font-semibold tabular-nums text-white">{when(goal)}</span>}
          </div>
          {why && (
            <p id="stage-mode-why" className="m-0 bg-court-bar px-3 pb-2 text-[15px] text-court-text" data-testid="stage-mode-why">
              {why}
              {fieldOpen && staff && (
                <>
                  {" "}
                  <Link href={`/app/${orgId}/matches/${match.id}/check`} className="font-semibold text-white underline underline-offset-4">
                    {t("fieldCheck")}
                  </Link>
                </>
              )}
            </p>
          )}
          {/* one video element; the picture fits the screen beside the controls (UI-05) */}
          <div hidden={mode !== "video"} className="mx-auto w-full lg:max-w-[calc((100svh-12rem)*16/9)]">
            {goal?.t_ms != null ? (
              // one scene at a time: the window of the goal; «Alle abspielen» goes on by itself
              <VideoPlayer
                ref={player}
                key={`${goal.event_id}-${all}`}
                src={`${media}/hls/master.m3u8`}
                poster={video.has_poster ? `${media}/poster.jpg` : undefined}
                fps={video.fps}
                window={free ? undefined : sceneOf(goal)}
                onWindowEnd={() => (all ? step(1) : setEnded(true))}
                onKey={onKey}
                autoPlay={all}
              />
            ) : (
              <VideoPlayer ref={player} src={`${media}/hls/master.m3u8`} poster={video.has_poster ? `${media}/poster.jpg` : undefined} fps={video.fps} markers={partMarkers} />
            )}
          </div>
          {mode === "video" && ended && !all && (
            <p role="status" className="m-0 flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-rule px-3 py-1.5 text-[15px]" data-testid="scene-ended">
              <b>{t("sceneEnded")}</b>
              {at >= 0 && at < list.length - 1 && (
                <button type="button" onClick={() => step(1)} className="min-h-11 cursor-pointer font-bold underline decoration-[1.5px] underline-offset-4">
                  {t("nextScene")}
                </button>
              )}
              <button
                type="button"
                onClick={() => (setFree(true), setEnded(false), player.current?.play())}
                className="min-h-11 cursor-pointer font-bold underline decoration-[1.5px] underline-offset-4"
                data-testid="scene-run-on"
              >
                {t("letItRun")}
              </button>
            </p>
          )}
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
            />
          )}
        </div>
        <div className="min-w-0">
        {/* the legend belongs to the dots of «Feld von oben», not to the video (UI-06) */}
        {mode === "taktik" && <CameraKey us={ownName} them={oppName} referee={t("referee")} ball={t("ball")} />}
        <div className="mt-4 flex flex-wrap gap-3" data-testid="stage-actions">
          {/* the scenes one after the other, also without a thing (UX-03) */}
          {list.length > 1 && (
            <>
              <Button variant="secondary" onClick={() => step(-1)} disabled={at <= 0} data-testid="prev-scene">
                <SkipBack aria-hidden />
                {t("prevScene")}
              </Button>
              <Button variant={chosen ? "primary" : "secondary"} onClick={() => step(1)} disabled={at >= list.length - 1} data-testid="next-scene">
                {t("nextScene")}
                <SkipForward aria-hidden />
              </Button>
            </>
          )}
          {chosen && (
            <Button variant="secondary" aria-pressed={all} onClick={() => (choose("video"), setAll((x) => !x))} data-testid="play-all">
              {all ? t("stopAll") : t("playAll", { n: list.length })}
            </Button>
          )}
          <Button variant={chosen ? "secondary" : "primary"} aria-pressed={isKept} onClick={() => void keep()} disabled={goal?.t_ms == null} data-testid="keep-scene">
            {isKept && <Check aria-hidden />}
            {isKept ? t("kept") : t("keepScene")}
          </Button>
          {/* where the saved scene is: the scenes of this match (BUG-21) */}
          {isKept && (
            <Link href={`/app/${orgId}/teams/${match.team_id}/scenes?match=${match.id}`} className="inline-flex min-h-11 items-center text-[15px] font-bold text-ink underline decoration-[1.5px] underline-offset-4" data-testid="kept-where">
              {t("keptWhere")}
            </Link>
          )}
          {/* drawing is on the video: the workbench opens with the tools on this moment (BUG-13) */}
          {staff && mode === "video" && onDraw && (
            <Button
              variant="secondary"
              onClick={() => {
                player.current?.pause();
                onDraw(Math.round(player.current?.time() ?? (goal ? sceneOf(goal).start_ms : 0)));
              }}
              data-testid="stage-draw"
            >
              {t("draw")}
            </Button>
          )}
        </div>
        {list.length > 1 && mode === "video" && <p className="mt-2 mb-0 text-[15px] text-ink-2 max-md:hidden">{t("sceneKeys")}</p>}
        {/* no throw-off: the Rail over the video's own time, the goals at their place in it (G8) */}
        {!span && goals.length > 0 && goals.every((g) => g.minute == null) && video.duration_s ? (
          <div className="mt-6">
            <Rail
              goals={goals.filter((g) => g.t_ms != null).map((g) => ({ minute: g.t_ms! / 60_000, team: g.team === "opp" ? "opp" : "own" }))}
              at={goal?.t_ms != null ? goal.t_ms / 60_000 : null}
              length={Math.max(1, video.duration_s / 60)}
              label={t("rail")}
              oppFirst={railOppFirst}
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
                <Rail goals={reportGoals(graphics)} phase={short ? null : phase} at={goal?.minute ?? null} from={span[0]} length={Math.max(1, span[1] - span[0])} label={t("rail")} oppFirst={railOppFirst} />
                <p className="mt-1 flex justify-between text-[15px] text-ink-2" data-testid="rail-span">
                  <span>{t("minuteAt", { n: Math.floor(span[0]) })}</span>
                  <span>{t("minuteAt", { n: Math.ceil(span[1]) })}</span>
                </p>
              </>
            ) : (
              <>
                <Rail goals={reportGoals(graphics)} phase={phase} at={goal?.minute ?? null} label={t("rail")} oppFirst={railOppFirst} />
                <p className="mt-1 flex justify-between text-[15px] text-ink-2">
                  <span>{t("throwOff")}</span>
                  <span>{t("halfTimeWord")}</span>
                  <span>{t("fullTime")}</span>
                </p>
              </>
            )}
          </div>
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
                {/* the running scene by its background and a bar, its place of the shot kept;
                    the team by its colour dot and name, the time once (UX-04) */}
                <button
                  type="button"
                  aria-pressed={on}
                  onClick={() => pick(g.event_id)}
                  className={cn(
                    "grid min-h-11 w-full cursor-pointer grid-cols-[28px_52px_minmax(0,1fr)] gap-2 border-t border-rule px-3 py-2.5 text-left",
                    on ? "bg-attn text-attn-ink shadow-[inset_4px_0_0_var(--ink)]" : "bg-transparent text-ink hover:bg-ink/5",
                  )}
                >
                  <b className="font-num text-[17px]">{chosen ? i + 1 : ""}</b>
                  <b className="font-num text-[17px]">{when(g)}</b>
                  <span className="text-[15px] leading-snug">
                    <i
                      aria-hidden
                      className={cn(
                        "mr-1.5 inline-block size-3 rounded-full align-[-1px]",
                        g.team === "opp" ? "bg-opp-cam shadow-[inset_0_0_0_2.5px_var(--opp-cam-edge),0_0_0_1px_var(--ink)]" : "bg-club-cam shadow-[0_0_0_1px_var(--ink)]",
                      )}
                    />
                    {t("goalOf", { team: team(g), clock: "" }).trim()}
                    <small className={cn("block text-[15px]", on ? "text-attn-ink" : "text-ink-2")}>{where(g)}</small>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
        {/* the running scene's place of the shot, changed with two taps (fourth real-video test H7) */}
        {goal && goal.has_video && (
          <p className="m-0 flex flex-wrap items-center justify-between gap-x-3 border-t border-rule px-3 py-1.5 text-[15px]" data-testid="stage-spot">
            <span className="text-ink-2">{spotText(goal)}</span>
            {staff && <SpotChange orgId={orgId} matchId={match.id} goal={goal} label={label(goal)} clip={{ src: `${media}/hls/master.m3u8`, window: sceneOf(goal) }} />}
          </p>
        )}
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
            {staff ? t("plainBench") : t("plainComments")}
          </button>
        </p>
        <details className="mt-6">
          <summary className="fold font-bold">
            {t("sceneList")} ({goals.length})
          </summary>
          <ul className="m-0 mt-2 max-h-[420px] list-none overflow-y-auto p-0">
            {goals.map((g) => (
              <li key={g.event_id}>
                <button type="button" onClick={() => (onThing(null), pick(g.event_id))} className="flex min-h-11 w-full cursor-pointer items-center gap-3 border-t border-rule bg-transparent px-1 text-left text-[15px] text-ink hover:bg-ink/5" aria-pressed={g.event_id === eventId}>
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

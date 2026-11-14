"use client";
import Link from "next/link";

import { useTranslations } from "next-intl";
import { type ReactNode, useState } from "react";
import { buttonClass } from "@/components/ui/button";
import { cameraScene, goalRuns, useSceneCamera, type MatchGraphics } from "@/lib/graphics";
import { threeThings, type Thing } from "@/lib/three-things";
import { formatClock } from "@/lib/format";
import { cn } from "@/lib/utils";
import { LineKey } from "./blocks";
import { Bundle, EmptyField } from "./bundle";
import { SpotChange, SpotStatus, useSpotText } from "./spot-parts";
import { TacticsCamera } from "./tactics-camera";

/** The match clock of a minute, to the full second as a scoreboard shows it: one rounding on every screen (fourth real-video test H8). */
export function clockOf(minute: number | null | undefined): string {
  if (minute == null) return "";
  return formatClock(minute * 60_000 + 1);
}

/** The sentence of a thing, e.g. "Gegentore über rechts aussen". */
export function useThingText() {
  const t = useTranslations("anlauf");
  return (x: Thing) => {
    const zone = x.zone ? t(`zoneFrom.${x.zone}` as "zoneFrom.la") : "";
    return t(x.key === "conceded_zone" ? "thing_conceded_zone" : x.key === "scored_zone" ? "thing_scored_zone" : "thing_conceded_fast_breaks", { zone });
  };
}

/**
 * Drei Dinge (SPEC 7.1, 7.2): index, numeral, base, sentence, the bundle of runs, the scenes.
 * Punkt 1 switches in the same frame between all its goals and one scene on the tactics camera.
 * `onScenes` opens the scenes of a thing (the video tab or the scene search).
 */
export function ThreeThingsView({
  orgId,
  matchId,
  graphics,
  oppName,
  onScenes,
  hrefScenes,
  onScene,
}: {
  orgId: string;
  matchId: string;
  graphics: MatchGraphics;
  oppName: string;
  /** opens one goal's scene (the Video tab at that scene); without it the scene shows here */
  onScene?: (eventId: string) => void;
  /** opens the scenes of a thing; `n` is its place (1 to 3), as in `?thing=n` */
  onScenes?: (thing: Thing, n: number) => void;
  hrefScenes?: (thing: Thing, n: number) => string;
}) {
  const t = useTranslations("anlauf");
  const text = useThingText();
  const things = threeThings(goalRuns(graphics));
  if (things.length === 0) {
    // confirmed goals, but not enough with a spot for three things: the goals themselves, as
    // scenes and on the tactics camera (real-video test E01)
    if (graphics.goals.some((x) => x.has_video)) return <VideoGoals orgId={orgId} matchId={matchId} graphics={graphics} oppName={oppName} onScene={onScene} />;
    return <p className="border-t-2 border-ink pt-4 text-[17px] text-ink-2">{t("noThings")}</p>;
  }
  return (
    <div>
      {/* one thing fills the row (figure and text left, the bundle large right), two share it */}
      <ol className={cn("m-0 grid list-none grid-cols-1 border-t-2 border-ink p-0", things.length === 2 ? "md:grid-cols-2" : things.length >= 3 && "md:grid-cols-3")} data-testid="three-things">
        {things.map((x, i) => (
          <li
            key={x.key}
            className={cn(
              "flex flex-col gap-2 border-rule py-4 max-md:border-b md:px-[22px] md:pt-[18px] md:pb-[22px]",
              i > 0 && "md:border-l",
              i === 0 && "md:pl-0",
              i === things.length - 1 && "md:pr-0",
              things.length === 1 && "md:grid md:grid-cols-[minmax(0,1fr)_minmax(0,480px)] md:content-start md:gap-x-12",
            )}
          >
            <p className="m-0 w-full font-mono text-[13px] font-bold text-ink">{t("index", { n: i + 1, total: things.length })}</p>
            <p className="m-0 flex flex-wrap items-baseline gap-x-2.5">
              <b className={cn("font-num text-[64px] leading-[.8] md:text-[96px]", x.team === "own" ? "text-club-text" : "text-ink")}>{x.value}</b>
              <span className="font-slant text-base text-ink-2 md:text-[22px]">{x.key === "conceded_fast_breaks" ? t("unitFastBreaks") : t("unitOf", { of: x.of ?? 0 })}</span>
            </p>
            <h3 className="m-0 text-[17px] leading-[1.22] font-bold md:text-xl">{text(x)}</h3>
            <div className={cn(things.length === 1 && "md:col-start-2 md:row-span-6 md:row-start-1")}>
              {i === 0 ? <FirstThing orgId={orgId} matchId={matchId} thing={x} label={text(x)} oppName={oppName} /> : <ThingBundle thing={x} label={text(x)} />}
            </div>
            {(onScenes || hrefScenes) &&
              (hrefScenes ? (
                <a href={hrefScenes(x, i + 1)} className={buttonClass("primary", "sm", "mt-auto self-start")}>
                  {t("scenes", { count: x.goals.length })}
                </a>
              ) : (
                <button type="button" onClick={() => onScenes?.(x, i + 1)} className={buttonClass("primary", "sm", "mt-auto self-start")}>
                  {t("scenes", { count: x.goals.length })}
                </button>
              ))}
          </li>
        ))}
      </ol>
      {/* goals still without their place: how many, and the way to add them (H7) */}
      <SpotStatus orgId={orgId} matchId={matchId} graphics={graphics} things={things.length} compact />
      <LineKey
        className="mt-3"
        // only what is drawn: without a run (no confirmed court) no «Weg zum Wurf» in the key
        items={[
          ...(things.some((x) => x.goals.some((g) => g.run.length > 1 && g.confirmed)) ? [{ label: t("keyConfirmed") }] : []),
          ...(things.some((x) => x.goals.some((g) => g.run.length > 1 && !g.confirmed)) ? [{ label: t("keyEstimated"), estimated: true }] : []),
          { label: t("keyToGoal") },
        ]}
      />
    </div>
  );
}

function ThingBundle({ thing, label, width = 360 }: { thing: Thing; label: string; width?: number }) {
  const t = useTranslations("anlauf");
  const estimated = thing.goals.filter((g) => !g.confirmed).length;
  return (
    <div className="my-1.5">
      <Bundle goals={thing.goals} rest={thing.rest} width={width} play label={t("bundleLabel", { count: thing.goals.length, thing: label, estimated })} />
    </div>
  );
}

/** Punkt 1: all its goals as a bundle, or one of them on the tactics camera. */
function FirstThing({ orgId, matchId, thing, label, oppName }: { orgId: string; matchId: string; thing: Thing; label: string; oppName: string }) {
  const t = useTranslations("anlauf");
  const [scene, setScene] = useState<string | null>(null);
  const first = thing.goals.find((g) => g.eventId)?.eventId ?? null;
  const goal = thing.goals.find((g) => g.eventId === (scene ?? first));
  return (
    <>
      <div className="flex" role="group">
        <button
          type="button"
          aria-pressed={scene == null}
          onClick={() => setScene(null)}
          className={cn("min-h-11 cursor-pointer border-[1.5px] border-ink px-3 text-[15px] font-bold", scene == null ? "bg-ink text-ground" : "bg-transparent text-ink")}
        >
          {t("all", { count: thing.goals.length })}
        </button>
        {first && (
          <button
            type="button"
            aria-pressed={scene != null}
            onClick={() => setScene(first)}
            className={cn("-ml-[1.5px] min-h-11 cursor-pointer border-[1.5px] border-ink px-3 text-[15px] font-bold", scene != null ? "bg-ink text-ground" : "bg-transparent text-ink")}
          >
            {t("sceneAt", { clock: clockOf(goal?.minute) })}
          </button>
        )}
      </div>
      {scene ? (
        <SceneCamera orgId={orgId} matchId={matchId} eventId={scene} label={t("goalOf", { team: thing.team === "opp" ? oppName : t("us"), clock: clockOf(goal?.minute) })} />
      ) : (
        <ThingBundle thing={thing} label={label} />
      )}
    </>
  );
}

/** One scene on the tactics camera, or the empty field when nothing was measured. */
export function SceneCamera({
  orgId,
  matchId,
  eventId,
  label,
  view = "halfB",
  width = 340,
  caption,
  captionSmall,
  barExtra,
}: {
  orgId: string;
  matchId: string;
  eventId: string;
  label: string;
  view?: "halfB" | "camL";
  width?: number;
  caption?: string;
  captionSmall?: string;
  barExtra?: ReactNode;
}) {
  const t = useTranslations("anlauf");
  const q = useSceneCamera(orgId, matchId, eventId);
  const scene = q.data ? cameraScene(q.data, label) : null;
  if (q.isLoading) return <div className="aspect-[21/17] bg-court" aria-busy="true" />;
  if (!scene) {
    // the court not confirmed yet: no positions, the question instead, and the way to answer it
    const ask = q.data != null && q.data.field_confirmed === false;
    return (
      <div className="my-1.5" data-testid={ask ? "camera-field-question" : "camera-empty"}>
        <div className="relative">
          <EmptyField label={t("noCamera")} />
          <div className="absolute top-1/2 left-1/2 w-[min(26rem,calc(100%-2rem))] -translate-x-1/2 -translate-y-1/2 bg-paper px-4 py-3 text-center">
            <p className="m-0 text-[15px] font-bold text-ink">{ask ? t("fieldQuestion") : t("noCamera")}</p>
            {ask && <p className="m-0 mt-1 text-[15px] text-ink-2">{t("fieldHint")}</p>}
            {ask && (
              <Link href={`/app/${orgId}/matches/${matchId}/check`} className="mt-2 inline-flex min-h-11 items-center font-semibold text-ink underline decoration-2 underline-offset-4" data-testid="camera-to-check">
                {t("fieldCheck")}
              </Link>
            )}
          </div>
        </div>
        {barExtra && <div className="flex items-center gap-2.5 bg-court-bar px-3 py-2">{barExtra}</div>}
      </div>
    );
  }
  return (
    <>
      <TacticsCamera
        scene={scene}
        view={view}
        width={width}
        dot={view === "halfB" ? 17 : 14}
        text={{ label: t("cameraLabel", { label }), pause: t("pause"), play: t("play"), notFound: t("ballNotFound"), noBall: t("noBall"), caption: caption ?? null, captionSmall: caption ? (captionSmall ?? t("positionsFromVideo")) : null, clockPrefix: scene.videoTime ? t("videoShort") : null }}
        barExtra={barExtra}
      />
      {/* the count of dots is not reliable yet: said plainly (G3, Q-REC-OFFCOURT) */}
      {q.data?.source === "analysis" && (
        <p className="m-0 mt-1.5 text-[15px] text-ink-2" data-testid="camera-estimate">
          {t("positionsEstimated")}
        </p>
      )}
    </>
  );
}

const mmss = formatClock;

/**
 * The goals of a match without three things yet: each with its time (match clock, else the place
 * in the video), the team, the place of the shot («Wurfort fehlt», «Wurfort ändern»), and the scene on the tactics
 * camera (E01, E02).
 */
export function VideoGoals({ orgId, matchId, graphics, oppName, onScene }: { orgId: string; matchId: string; graphics: MatchGraphics; oppName: string; onScene?: (eventId: string) => void }) {
  const t = useTranslations("anlauf");
  const goals = graphics.goals.filter((x) => x.has_video).sort((a, b) => (a.minute ?? Infinity) - (b.minute ?? Infinity) || (a.t_ms ?? 0) - (b.t_ms ?? 0));
  const playable = goals.filter((g) => g.has_video && g.t_ms != null);
  const [open, setOpen] = useState<string | null>(playable[0]?.event_id ?? null);
  const shown = goals.find((g) => g.event_id === open);
  const when = (g: (typeof goals)[number]) => (g.minute != null ? clockOf(g.minute) : g.t_ms != null ? t("atVideo", { time: mmss(g.t_ms) }) : "");
  const who = (g: (typeof goals)[number]) => (g.team === "own" ? t("us") : oppName);
  const spotText = useSpotText();
  return (
    <section className="border-t-2 border-ink pt-4" data-testid="video-goals">
      {/* honest and with a way: how many goals have a place, what is missing, «nachtragen» (H7) */}
      <SpotStatus orgId={orgId} matchId={matchId} graphics={graphics} things={0} />
      <div className="mt-4 grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,520px)]">
        <ol className="m-0 list-none p-0" aria-label={t("videoGoalsTitle")}>
          {goals.map((g) => (
            <li key={g.event_id} className="flex min-h-11 flex-wrap items-center gap-x-3 gap-y-1 border-b border-rule py-2 text-[17px]" data-testid="video-goal">
              <b className="font-num w-20 shrink-0">{when(g)}</b>
              <span aria-hidden className={cn("inline-block h-2.5 w-3 -skew-x-12", g.team === "own" ? "bg-club-text" : "bg-ink")} />
              <span className="min-w-0 flex-1">
                {t("goalBy", { team: who(g) })}
                {g.number != null && ` · #${g.number}`}
                {/* the place and its change on their own line: on a phone the row stays readable */}
                <span className="flex flex-wrap items-center gap-x-3 text-[15px] text-ink-2">
                  <span data-testid="video-goal-spot">{spotText(g)}</span>
                  <SpotChange orgId={orgId} matchId={matchId} goal={g} label={`${t("goalBy", { team: who(g) })} · ${when(g)}`} />
                </span>
              </span>
              {g.has_video && g.t_ms != null && (
                <button type="button" onClick={() => (onScene ? onScene(g.event_id) : setOpen(g.event_id))} aria-pressed={onScene ? undefined : open === g.event_id} data-testid="scene-show" className="min-h-11 cursor-pointer border-0 bg-transparent p-0 text-[15px] font-bold text-ink underline decoration-[1.5px] underline-offset-4">
                  {t("sceneShow")}
                </button>
              )}
            </li>
          ))}
        </ol>
        {shown && <SceneCamera key={shown.event_id} orgId={orgId} matchId={matchId} eventId={shown.event_id} label={`${who(shown)} ${when(shown)}`} view="halfB" width={520} />}
      </div>
    </section>
  );
}

"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { buttonClass } from "@/components/ui/button";
import { cameraScene, goalRuns, useSceneCamera, type MatchGraphics } from "@/lib/graphics";
import { threeThings, type Thing } from "@/lib/three-things";
import { cn } from "@/lib/utils";
import { LineKey } from "./blocks";
import { Bundle, EmptyField } from "./bundle";
import { TacticsCamera } from "./tactics-camera";

export function clockOf(minute: number | null | undefined): string {
  if (minute == null) return "";
  const s = Math.round(minute * 60);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
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
}: {
  orgId: string;
  matchId: string;
  graphics: MatchGraphics;
  oppName: string;
  onScenes?: (thing: Thing) => void;
  hrefScenes?: (thing: Thing) => string;
}) {
  const t = useTranslations("anlauf");
  const text = useThingText();
  const things = threeThings(goalRuns(graphics));
  if (things.length === 0) {
    return <p className="border-t-2 border-ink pt-4 text-[17px] text-ink-2">{t("noThings")}</p>;
  }
  return (
    <div>
      <ol className="m-0 grid list-none grid-cols-1 border-t-2 border-ink p-0 md:grid-cols-3" data-testid="three-things">
        {things.map((x, i) => (
          <li key={x.key} className={cn("flex flex-col gap-2 border-rule py-4 max-md:border-b md:px-[22px] md:pt-[18px] md:pb-[22px]", i > 0 && "md:border-l", i === 0 && "md:pl-0", i === things.length - 1 && "md:pr-0")}>
            <p className="m-0 w-full font-mono text-[13px] font-bold text-ink-2">{t("index", { n: i + 1, total: things.length })}</p>
            <p className="m-0 flex flex-wrap items-baseline gap-x-2.5">
              <b className={cn("font-num text-[64px] leading-[.8] md:text-[96px]", x.team === "own" ? "text-club-text" : "text-ink")}>{x.value}</b>
              <span className="font-slant text-base text-ink-2 md:text-[22px]">{x.key === "conceded_fast_breaks" ? t("unitFastBreaks") : t("unitOf", { of: x.of ?? 0 })}</span>
            </p>
            <h3 className="m-0 text-[17px] leading-[1.22] font-bold md:text-xl">{text(x)}</h3>
            {i === 0 ? (
              <FirstThing orgId={orgId} matchId={matchId} thing={x} label={text(x)} oppName={oppName} />
            ) : (
              <ThingBundle thing={x} label={text(x)} />
            )}
            {(onScenes || hrefScenes) &&
              (hrefScenes ? (
                <a href={hrefScenes(x)} className={buttonClass("primary", "sm", "mt-auto self-start")}>
                  {t("scenes", { count: x.goals.length })}
                </a>
              ) : (
                <button type="button" onClick={() => onScenes?.(x)} className={buttonClass("primary", "sm", "mt-auto self-start")}>
                  {t("scenes", { count: x.goals.length })}
                </button>
              ))}
          </li>
        ))}
      </ol>
      <LineKey
        className="mt-3"
        items={[
          { label: t("keyConfirmed") },
          { label: t("keyEstimated"), estimated: true },
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
          className={cn("min-h-11 cursor-pointer border-[1.5px] border-ink px-3 text-[13px] font-bold", scene == null ? "bg-ink text-ground" : "bg-transparent text-ink")}
        >
          {t("all", { count: thing.goals.length })}
        </button>
        {first && (
          <button
            type="button"
            aria-pressed={scene != null}
            onClick={() => setScene(first)}
            className={cn("-ml-[1.5px] min-h-11 cursor-pointer border-[1.5px] border-ink px-3 text-[13px] font-bold", scene != null ? "bg-ink text-ground" : "bg-transparent text-ink")}
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
export function SceneCamera({ orgId, matchId, eventId, label, view = "halfB", width = 340, caption }: { orgId: string; matchId: string; eventId: string; label: string; view?: "halfB" | "camL"; width?: number; caption?: string }) {
  const t = useTranslations("anlauf");
  const q = useSceneCamera(orgId, matchId, eventId);
  const scene = q.data ? cameraScene(q.data, label) : null;
  if (q.isLoading) return <div className="aspect-[21/17] bg-court" aria-busy="true" />;
  if (!scene) {
    return (
      <div className="relative my-1.5">
        <EmptyField label={t("noCamera")} />
        <p className="absolute inset-x-0 top-1/2 m-0 -translate-y-1/2 text-center text-[13px] font-semibold text-ink-2">{q.data && !q.data.field_confirmed ? t("fieldQuestion") : t("noCamera")}</p>
      </div>
    );
  }
  return (
    <TacticsCamera
      scene={scene}
      view={view}
      width={width}
      dot={view === "halfB" ? 16 : 12}
      text={{ label: t("cameraLabel", { label }), pause: t("pause"), play: t("play"), notFound: t("ballNotFound"), noBall: t("noBall"), caption: caption ?? null, captionSmall: caption ? t("positionsFromVideo") : null }}
    />
  );
}

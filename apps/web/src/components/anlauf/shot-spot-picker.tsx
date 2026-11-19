"use client";

import { useTranslations } from "next-intl";
import { type MouseEvent, useRef } from "react";
import {
  COURT_ZONES,
  type CourtZone,
  halfToCourt,
  orientationBox,
  orientationMatrix,
  polygonPath,
  type SpotAnswer,
  type SpotOrientation,
  type SpotZone,
  tapAnswer,
  toPicture,
  ZONE_AREA,
  ZONE_LABEL_AT,
  ZONE_LABEL_SIDE,
} from "@/lib/shot-spot";
import { cn } from "@/lib/utils";
import { HalfCourtLines } from "./court";
import type { Pt } from "./geometry";

const NS = { vectorEffect: "non-scaling-stroke" } as const;

/**
 * «Von wo?» (fourth real-video test H7): the attacked half, six places to tap, Siebenmeter and
 * Gegenstoss as keys and a quiet «Weiss nicht». One tap answers; there is no «Weiter».
 *
 * With `onSkip` (Prüfen, after a confirmed goal) the place is offered, not asked (W33): instead of
 * «Weiss nicht» an «Überspringen» key as large as the others, which saves nothing and goes on.
 *
 * The court lies as the camera sees it when the goal's side in the video is known (real-clip test:
 * with the goal always at the top, the coach had to turn it in his head for every attack on the
 * left goal): the attacked goal on the left or right as in the video, the far sideline at the top,
 * the words upright where their places are. Without it the goal is at the top. The names keep the
 * attacker's view («Aussen links» is the attacker's left wing). The coach's own earlier answer is
 * marked «Bisher». The estimate from the tracks is preselected as «Vorschlag» (A22): lighter, with
 * a dashed edge and a line under the court; one tap on it confirms it (the zone alone, the API
 * takes the estimated point over), a tap elsewhere sets another place as before.
 */
export function ShotSpotPicker({
  current,
  suggested,
  orientation = "top",
  onPick,
  onSkip,
  disabled,
}: {
  /** the place the coach gave before («Bisher») */
  current?: SpotZone | null;
  /** the estimate nobody confirmed yet («Vorschlag»); ignored next to the coach's own answer */
  suggested?: CourtZone | null;
  orientation?: SpotOrientation;
  /** the answer and, for a tap on the court, the point in court metres (attacked goal at x = 40) */
  onPick: (answer: SpotAnswer, point?: Pt) => void;
  /** the place is optional: «Überspringen» in the row of keys, equal to them, instead of «Weiss nicht» */
  onSkip?: () => void;
  disabled?: boolean;
}) {
  const t = useTranslations("spot");
  const court = useRef<SVGGElement>(null);
  const side = orientation !== "top";
  // the coach's own answer wins over the estimate
  const offer = current ? null : (suggested ?? null);
  const mark = (z: SpotZone) => (current === z ? t("current") : offer === z ? t("suggested") : null);
  // words at 14 px and more on a 360 px phone, also on the court turned on its side
  const font = side ? 1.3 : 0.95;

  const tap = (zone: CourtZone, e: MouseEvent<SVGElement>) => {
    if (disabled) return;
    // a pointer tap gives the place on the court (through the turned group: half-court metres);
    // a key gives only the zone, and so does a tap on the suggestion: it confirms the estimate
    const m = court.current?.getScreenCTM();
    let point: Pt | undefined;
    if (m && e.detail > 0) {
      const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(m.inverse());
      point = halfToCourt([Math.min(20, Math.max(0, p.x)), Math.min(16, Math.max(0, p.y))]);
    }
    const a = tapAnswer(zone, offer, point);
    onPick(a.answer, a.point);
  };

  const keys = (
    <>
      {(["m7", "gs"] as const).map((z) => {
        const word = mark(z);
        return (
          <button
            key={z}
            type="button"
            disabled={disabled}
            onClick={() => onPick(z)}
            data-testid={`spot-${z}`}
            className={cn("flex min-h-12 cursor-pointer flex-col items-start justify-center border-2 border-ink px-2.5 text-left text-[15px] font-semibold text-ink sm:px-4 sm:text-[17px] md:min-h-14", word ? "bg-attn" : "bg-transparent")}
          >
            {t(`zone.${z}` as "zone.m7")}
            {word && <span className="text-[14px] font-semibold italic">{word}</span>}
          </button>
        );
      })}
      {onSkip ? (
        <button type="button" onClick={onSkip} className="flex min-h-12 cursor-pointer items-center border-2 border-ink bg-transparent px-2.5 text-left text-[15px] font-semibold whitespace-nowrap text-ink sm:px-4 sm:text-[17px] md:min-h-14" data-testid="spot-skip">
          {t("skip")}
        </button>
      ) : (
        <button type="button" disabled={disabled} onClick={() => onPick("unknown")} className="min-h-12 cursor-pointer border-0 bg-transparent px-1 text-left text-[15px] font-bold whitespace-nowrap text-ink underline underline-offset-4 sm:text-[17px]" data-testid="spot-unknown">
          {t("unknown")}
        </button>
      )}
    </>
  );

  const field = (
    <svg viewBox={orientationBox(orientation).join(" ")} role="group" aria-label={side ? t("courtLabelVideo", { side: orientation }) : t("courtLabel")} className="court-frame block touch-manipulation select-none" data-orientation={orientation}>
      <g ref={court} transform={`matrix(${orientationMatrix(orientation).join(" ")})`}>
        <HalfCourtLines />
        {COURT_ZONES.map((z) => (
          <path
            key={z}
            d={polygonPath(ZONE_AREA[z])}
            role="button"
            tabIndex={disabled ? -1 : 0}
            aria-label={mark(z) ? `${t(`zone.${z}` as "zone.la")}, ${mark(z)}` : t(`zone.${z}` as "zone.la")}
            aria-disabled={disabled || undefined}
            data-testid={`spot-zone-${z}`}
            onClick={(e) => tap(z, e)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                if (!disabled) onPick(z);
              }
            }}
            data-suggested={offer === z || undefined}
            className={cn(
              "cursor-pointer outline-none [stroke:var(--ink)] [stroke-opacity:.3] [stroke-width:1px] hover:[fill:rgb(22_23_26/.07)] focus-visible:[stroke-opacity:1] focus-visible:[stroke-width:3px]",
              current === z ? "[fill:var(--attn)]" : offer === z ? "[fill:var(--attn)] [fill-opacity:.45] [stroke-dasharray:6_4] [stroke-opacity:1] [stroke-width:2px] hover:[fill:var(--attn)] hover:[fill-opacity:.7]" : "[fill:transparent]",
            )}
            {...NS}
          />
        ))}
      </g>
      {/* the words stay upright wherever the court lies */}
      {COURT_ZONES.map((z) => {
        const word = mark(z);
        const [lx, ly] = toPicture(orientation, (side ? ZONE_LABEL_SIDE : ZONE_LABEL_AT)[z]);
        const [l1, l2] = t(`zone2.${z}` as "zone2.la").split("|");
        const lines = (l2 ? 2 : 1) + (word ? 1 : 0);
        const y0 = side ? ly - ((lines - 1) * font * 1.1) / 2 + font * 0.35 : ly;
        return (
          <text
            key={z}
            x={lx}
            y={y0}
            textAnchor="middle"
            fontSize={font}
            fontWeight={700}
            fill="var(--ink)"
            // a halo in the area's colour: the court lines do not run through the words
            stroke={current === z ? "var(--attn)" : "var(--ground)"}
            strokeWidth={0.28}
            strokeLinejoin="round"
            paintOrder="stroke"
            pointerEvents="none"
            aria-hidden
          >
            <tspan x={lx} dy={0}>
              {l1}
            </tspan>
            {l2 && (
              <tspan x={lx} dy={font * 1.15}>
                {l2}
              </tspan>
            )}
            {word && (
              <tspan x={lx} dy={font * 1.3} fontSize={font * 0.86} fontWeight={600} fontStyle="italic">
                {word}
              </tspan>
            )}
          </text>
        );
      })}
    </svg>
  );

  return (
    <div data-testid="spot-picker">
      {side ? (
        // on its side the court is taller than wide: the keys go beside it, the width is used
        <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-2.5">
          {field}
          <div className="flex w-[7.5rem] flex-col gap-2 sm:w-36">{keys}</div>
        </div>
      ) : (
        field
      )}
      {offer && (
        <p className="m-0 mt-1.5 text-[15px] leading-snug font-semibold text-ink" data-testid="spot-suggestion-note">
          {t("suggestedNote", { zone: t(`zone.${offer}` as "zone.la") })}
        </p>
      )}
      <p className="m-0 mt-1 text-[14px] leading-snug text-ink-2" data-testid="spot-side-note">
        {side ? t(orientation === "left" ? "sideVideoLeft" : "sideVideoRight") : t("sideNote")}
      </p>
      {!side && <div className="mt-2 grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] items-stretch gap-2">{keys}</div>}
    </div>
  );
}

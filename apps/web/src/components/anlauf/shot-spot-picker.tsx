"use client";

import { useTranslations } from "next-intl";
import { type MouseEvent, useRef } from "react";
import { COURT_ZONES, halfToCourt, polygonPath, type SpotAnswer, type SpotZone, ZONE_AREA, ZONE_LABEL_AT } from "@/lib/shot-spot";
import { cn } from "@/lib/utils";
import { HalfCourtLines } from "./court";
import { HALF_BOX, type Pt } from "./geometry";

const NS = { vectorEffect: "non-scaling-stroke" } as const;
// the drawn half court ends at 16 m; the box keeps the goal visible at the top
const BOX = [HALF_BOX[0], HALF_BOX[1], HALF_BOX[2], 17.4].join(" ");

/**
 * «Von wo?» (fourth real-video test H7): the attacked half with the goal at the top, as in the
 * bundles of the three things, six places to tap, then Siebenmeter and Gegenstoss as large keys
 * and a quiet «Weiss nicht». One tap answers; there is no «Weiter». Left and right are the
 * attacker's: «Aussen links» is on the left of the picture. A place the analysis estimated (or the
 * coach gave before) is marked in yellow with its word.
 */
export function ShotSpotPicker({
  suggestion,
  onPick,
  disabled,
}: {
  /** the place to mark: estimated from the tracks («Vorschlag») or given before («Bisher») */
  suggestion?: { zone: SpotZone; kind: "estimated" | "current" } | null;
  /** the answer and, for a tap on the court, the point in court metres (attacked goal at x = 40) */
  onPick: (answer: SpotAnswer, point?: Pt) => void;
  disabled?: boolean;
}) {
  const t = useTranslations("spot");
  const svg = useRef<SVGSVGElement>(null);
  const mark = (z: SpotZone) => (suggestion?.zone === z ? (suggestion.kind === "current" ? t("current") : t("suggested")) : null);

  const tap = (zone: (typeof COURT_ZONES)[number], e: MouseEvent<SVGElement>) => {
    if (disabled) return;
    // a pointer tap gives the place on the court; a key gives only the zone
    const el = svg.current;
    const m = el?.getScreenCTM();
    if (el && m && e.detail > 0) {
      const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(m.inverse());
      onPick(zone, halfToCourt([Math.min(20, Math.max(0, p.x)), Math.min(16, Math.max(0, p.y))]));
    } else onPick(zone);
  };

  return (
    <div data-testid="spot-picker">
      <svg ref={svg} viewBox={BOX} role="group" aria-label={t("courtLabel")} className="block w-full touch-manipulation select-none">
        <HalfCourtLines />
        {COURT_ZONES.map((z) => {
          const word = mark(z);
          const [lx, ly] = ZONE_LABEL_AT[z];
          const [l1, l2] = t(`zone2.${z}` as "zone2.la").split("|");
          return (
            <g key={z}>
              <path
                d={polygonPath(ZONE_AREA[z])}
                role="button"
                tabIndex={disabled ? -1 : 0}
                aria-label={word ? `${t(`zone.${z}` as "zone.la")}, ${word}` : t(`zone.${z}` as "zone.la")}
                aria-disabled={disabled || undefined}
                data-testid={`spot-zone-${z}`}
                onClick={(e) => tap(z, e)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    if (!disabled) onPick(z);
                  }
                }}
                className={cn(
                  "cursor-pointer outline-none [stroke:var(--ink)] [stroke-opacity:.3] [stroke-width:1px] hover:[fill:rgb(22_23_26/.07)] focus-visible:[stroke-opacity:1] focus-visible:[stroke-width:3px]",
                  word ? "[fill:var(--attn)]" : "[fill:transparent]",
                )}
                {...NS}
              />
              <text
                x={lx}
                y={ly}
                textAnchor="middle"
                fontSize={0.95}
                fontWeight={700}
                fill="var(--ink)"
                // a halo in the area's colour: the court lines do not run through the words
                stroke={word ? "var(--attn)" : "var(--ground)"}
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
                  <tspan x={lx} dy={1.1}>
                    {l2}
                  </tspan>
                )}
                {word && (
                  <tspan x={lx} dy={1.25} fontSize={0.82} fontWeight={600} fontStyle="italic">
                    {word}
                  </tspan>
                )}
              </text>
            </g>
          );
        })}
      </svg>
      {/* which way round, small under the court: read once, not before every tap */}
      <p className="m-0 mt-1 text-[14px] leading-snug text-ink-2">{t("sideNote")}</p>
      {/* the two kinds and «Weiss nicht» in one row: the whole step fits one phone screen */}
      <div className="mt-2 grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] items-stretch gap-2">
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
        <button type="button" disabled={disabled} onClick={() => onPick("unknown")} className="min-h-12 cursor-pointer border-0 bg-transparent px-1 text-[15px] font-bold whitespace-nowrap text-ink underline underline-offset-4 sm:text-[17px]" data-testid="spot-unknown">
          {t("unknown")}
        </button>
      </div>
    </div>
  );
}

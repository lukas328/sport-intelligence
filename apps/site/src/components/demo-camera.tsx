"use client";

import { REF, TacticsCamera, type CameraScene, type CameraText } from "@/components/anlauf/tactics-camera";
import { cn } from "@/lib/cn";

export type CameraLegendText = { own: string; opp: string; ref: string; number: string; ball: string };

/**
 * What the dots on the tactics camera are. Under the camera on the demo page; on the start page
 * it stands as a list in the text column next to it (S10).
 */
export function CameraLegend({ legend, list = false }: { legend: CameraLegendText; list?: boolean }) {
  const row = list ? "flex min-h-11 items-center gap-3 border-b border-rule py-2 font-semibold text-ink" : "inline-flex items-center gap-2";
  return (
    <ul className={list ? "border-t-2 border-ink text-[1.0625rem]" : "mt-3 flex flex-wrap gap-x-6 gap-y-2 text-base text-ink-2"}>
      <li className={row}>
        <i aria-hidden className="inline-block size-4 shrink-0 border-[1.5px] border-court bg-[var(--club-cam)]" style={{ borderRadius: "50%" }} />
        {legend.own}
      </li>
      <li className={row}>
        <i aria-hidden className="inline-block size-4 shrink-0 border-2 border-[var(--opp-cam-edge)] bg-[var(--opp-cam)] outline-1 outline-court" style={{ borderRadius: "50%" }} />
        {legend.opp}
      </li>
      <li className={row}>
        <i aria-hidden className="inline-block size-3 shrink-0 rotate-45" style={{ background: REF }} />
        <span className={cn(list && "ml-0.5")}>{legend.ref}</span>
      </li>
      <li className={cn(row, list && "font-normal")}>{legend.number}</li>
      <li className={cn(row, list && "font-normal")}>{legend.ball}</li>
    </ul>
  );
}

/** The tactics camera with its legend; the view turns on narrow screens (goal at the top). */
export function DemoCamera({
  scene,
  text,
  legend,
  view = "camL",
  desktopWidth = 1000,
  shotLabel = true,
  ballLine = true,
}: {
  scene: CameraScene;
  text: CameraText;
  /** the legend under the camera; left out where the page shows it elsewhere */
  legend?: CameraLegendText;
  view?: "camL" | "halfB";
  /** the width the desktop picture is drawn for (dots keep their size in pixels) */
  desktopWidth?: number;
  /** the label next to the shot spot; off where the caption already names the goal and the spot is at the edge */
  shotLabel?: boolean;
  /** the line of who held the ball (with its heading from `text.ballLine`) */
  ballLine?: boolean;
}) {
  return (
    <div className="on-court">
      <div className="hidden md:block">
        <TacticsCamera scene={scene} view={view} width={desktopWidth} dot={13} text={text} showLabels={shotLabel} ballLine={ballLine} />
      </div>
      <div className="md:hidden">
        <TacticsCamera scene={scene} view="halfB" width={358} dot={10} text={text} showLabels={false} ballLine={ballLine} />
      </div>
      {legend && <CameraLegend legend={legend} />}
    </div>
  );
}

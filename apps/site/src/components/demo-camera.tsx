"use client";

import { TacticsCamera, type CameraScene, type CameraText } from "@/components/anlauf/tactics-camera";

/** The tactics camera with its legend; the view turns on narrow screens (goal at the top). */
export function DemoCamera({
  scene,
  text,
  legend,
  view = "camL",
}: {
  scene: CameraScene;
  text: CameraText;
  legend: { own: string; opp: string; ref: string; number: string; ball: string };
  view?: "camL" | "halfB";
}) {
  return (
    <div className="on-court">
      <div className="hidden md:block">
        <TacticsCamera scene={scene} view={view} width={1000} dot={13} text={text} />
      </div>
      <div className="md:hidden">
        <TacticsCamera scene={scene} view="halfB" width={358} dot={10} text={text} />
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-base text-ink-2">
        <li className="inline-flex items-center gap-2">
          <i aria-hidden className="inline-block size-4 border-[1.5px] border-[#0a0d11] bg-[var(--club-cam)]" style={{ borderRadius: "50%" }} />
          {legend.own}
        </li>
        <li className="inline-flex items-center gap-2">
          <i aria-hidden className="inline-block size-4 border-2 border-[var(--opp-cam-edge)] bg-[var(--opp-cam)] outline-1 outline-[#0f2333]" style={{ borderRadius: "50%" }} />
          {legend.opp}
        </li>
        <li className="inline-flex items-center gap-2">
          <i aria-hidden className="inline-block size-3 rotate-45 bg-[#8d97a1]" />
          {legend.ref}
        </li>
        <li>{legend.number}</li>
        <li>{legend.ball}</li>
      </ul>
    </div>
  );
}

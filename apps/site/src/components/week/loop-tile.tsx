import { VIEWS } from "@/components/anlauf/geometry";
import { CameraFrame, type CameraScene } from "@/components/anlauf/tactics-camera";
import { DemoLink } from "@/components/kit";
import { When } from "@/components/story";
import type { Drill } from "@/lib/drills";
import { DrillSketch } from "./training-tip";

export interface LoopStep {
  title: string;
  text: string;
  href: string;
}

/**
 * «Was heisst das fürs Training?» on the start page (BEFUNDE-4 U30): the loop from a pattern to
 * training in four short steps, each with a small picture and a jump to its part of the demo
 * week: the pattern (11 of 29), why (one frame of a scene from above), the drill from the library,
 * the effect (the season bar, invented follow-up matches like on the demo page).
 */
export function LoopTile({
  kick,
  title,
  steps,
  link,
  demoHref,
  numeral,
  unit,
  scene,
  drill,
  drillLabel,
  bars,
}: {
  kick: string;
  title: string;
  steps: LoopStep[];
  link: string;
  demoHref: string;
  numeral: number;
  unit: string;
  scene: CameraScene;
  drill: Drill;
  drillLabel: string;
  bars: number[];
}) {
  const most = Math.max(...bars);
  const pictures = [
    <div key="m" className="flex h-full items-center justify-center gap-2 bg-paper">
      <b className="font-num text-[3.5rem] leading-none text-club-text">{numeral}</b>
      <span className="upright text-[1.125rem] text-ink-2">{unit}</span>
    </div>,
    <div key="w" className="on-court h-full bg-court">
      <svg viewBox={VIEWS.halfB.box.join(" ")} className="block h-full w-full" preserveAspectRatio="xMidYMin slice">
        <CameraFrame scene={scene} view="halfB" width={220} dot={8} t={0.86} />
      </svg>
    </div>,
    <div key="u" className="h-full overflow-hidden bg-paper [&_svg]:h-full [&_svg]:w-full">
      <DrillSketch drill={drill} label={drillLabel} />
    </div>,
    <div key="e" className="flex h-full items-end justify-center gap-2 bg-paper px-4 pt-3 pb-3">
      {bars.map((n, i) => (
        <i key={i} className={i === 0 ? "block w-5 bg-ink/30" : "block w-5 bg-club"} style={{ height: `${(n / most) * 100}%` }} />
      ))}
    </div>,
  ];
  return (
    <div className="border-2 border-ink bg-paper p-5 shadow-[8px_8px_0_var(--ink)] md:p-8">
      <When>{kick}</When>
      <h2 id="loop" className="mt-4 text-[2.25rem] md:text-[3rem]">
        {title}
      </h2>
      <ol className="mt-6 grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((s, i) => (
          <li key={s.title} className="min-w-0">
            <DemoLink href={s.href} className="group grid grid-cols-[7rem_minmax(0,1fr)] items-start gap-x-4 sm:grid-cols-1">
              <span aria-hidden className="block aspect-[4/3] overflow-hidden border-2 border-ink transition-transform duration-200 group-hover:-translate-y-0.5 motion-reduce:transition-none sm:aspect-[16/10]">
                {pictures[i]}
              </span>
              <span className="block min-w-0 sm:mt-3">
                <span className="flex items-baseline gap-2">
                  <span aria-hidden className="upright text-[1.375rem] leading-none text-club-text">
                    {i + 1}
                  </span>
                  <b className="text-[1.1875rem] leading-tight underline decoration-2 underline-offset-4 group-hover:decoration-[3px]">{s.title}</b>
                </span>
                <span className="mt-1 block text-[1.0625rem] text-ink-2">{s.text}</span>
              </span>
            </DemoLink>
          </li>
        ))}
      </ol>
      <DemoLink href={demoHref} className="link mt-4">
        {link}
      </DemoLink>
    </div>
  );
}

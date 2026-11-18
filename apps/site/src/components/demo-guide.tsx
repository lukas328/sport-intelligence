import { Bundle } from "@/components/anlauf/bundle";
import { Rail } from "@/components/anlauf/charts";
import { CameraFrame } from "@/components/anlauf/tactics-camera";
import { VIEWS } from "@/components/anlauf/geometry";
import type { ReportGoal } from "@/components/anlauf/flight-layout";
import type { CameraScene } from "@/components/anlauf/camera-types";
import type { ThingView } from "@/lib/things";

export interface GuideTile {
  id: string;
  title: string;
  text: string;
}

export interface ZoneBar {
  key: string;
  label: string;
  n: number;
  /** the zone of the first thing: drawn strong */
  strong: boolean;
}

/** the first thing's corner of the half court (goal to about 12 m) */
const THING_BOX = "-0.6 -1.2 21.2 13.25";

/**
 * «Was du hier siehst» on the demo page (BEFUNDE-2 L6): four small pictures of what is further
 * down, each a link that jumps there. The pictures are the page's own drawings in small (the first
 * thing, one frame of the scene from above, the run of the match, the score and the goals by position), so the
 * visitor recognises each part when he gets there.
 */
export function DemoGuide({
  title,
  lead,
  tiles,
  thing,
  scene,
  report,
  zones,
  score,
}: {
  title: string;
  lead: string;
  tiles: GuideTile[];
  thing: ThingView;
  scene: CameraScene;
  report: readonly ReportGoal[];
  zones: ZoneBar[];
  /** the final score, «27:29» */
  score: string;
}) {
  const most = Math.max(1, ...zones.map((z) => z.n));
  const pictures = [
    // 1 · the first thing: the numeral and its runs
    <div key="t" className="relative h-full bg-paper">
      <Bundle goals={thing.goals} width={260} clean box={THING_BOX} label="" className="h-full" />
      <p className="absolute top-2 left-3 flex items-baseline gap-1.5">
        <b className="font-num text-[2.25rem] leading-none text-club-text">{thing.numeral}</b>
        <span className="upright text-base text-ink-2">{thing.unit}</span>
      </p>
    </div>,
    // 2 · one frame of the scene on the tactics camera
    <div key="c" className="on-court h-full bg-court">
      <svg
        viewBox={VIEWS.halfB.box.join(" ")}
        className="block h-full w-full"
        preserveAspectRatio="xMidYMin slice"
      >
        <CameraFrame scene={scene} view="halfB" width={260} dot={8} t={0.82} />
      </svg>
    </div>,
    // 3 · the run of the match
    <div key="r" className="flex h-full flex-col justify-center bg-paper px-3">
      <Rail goals={report} label="" />
    </div>,
    // 4 · the score and the goals conceded by position, as columns
    <div key="z" className="flex h-full items-end gap-3 bg-paper px-3 pt-2 pb-3 md:gap-4 md:px-4">
      <b className="font-num self-start text-[1.75rem] leading-none md:text-[2.25rem]">{score}</b>
      <span className="flex h-[78%] flex-1 items-end justify-end gap-1 md:gap-1.5">
        {zones.map((z) => (
          <i
            key={z.key}
            className={z.strong ? "block w-3 bg-ink md:w-4" : "block w-3 bg-ink/25 md:w-4"}
            style={{ height: `${(z.n / most) * 100}%` }}
          />
        ))}
      </span>
    </div>,
  ];
  return (
    <nav aria-labelledby="guide" className="mt-8">
      <h2 id="guide" className="text-[1.75rem] md:text-[2.25rem]">
        {title}
      </h2>
      <p className="mt-2 max-w-[44rem] text-[1.125rem] text-ink-2">{lead}</p>
      <ol className="mt-6 grid grid-cols-2 gap-x-4 gap-y-6 md:gap-x-6 lg:grid-cols-4">
        {tiles.map((g, i) => (
          <li key={g.id} className="min-w-0">
            <a href={`#${g.id}`} className="group block">
              <span
                aria-hidden
                className="block aspect-[16/10] overflow-hidden border-2 border-ink shadow-[4px_4px_0_var(--ink)] transition-[transform,box-shadow] duration-200 group-hover:-translate-y-0.5 group-hover:shadow-[6px_7px_0_var(--ink)] motion-reduce:transition-none"
              >
                {pictures[i]}
              </span>
              <span className="mt-3 flex items-baseline gap-2">
                <span aria-hidden className="upright text-[1.5rem] leading-none text-club-text">
                  {i + 1}
                </span>
                <b className="text-[1.125rem] leading-tight underline decoration-2 underline-offset-4 group-hover:decoration-[3px]">
                  {g.title}
                </b>
              </span>
              <span className="mt-1 block text-base text-ink-2">{g.text}</span>
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

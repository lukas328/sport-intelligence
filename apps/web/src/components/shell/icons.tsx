import type { SVGProps } from "react";
import type { Dest } from "@/lib/nav-model";

/**
 * Own icons for the main navigation and the handball objects: one 20 px grid, 1.75 stroke,
 * square ends, drawn from the hall (court, scoreboard, jersey, cone). Lucide stays for neutral
 * controls only (close, search, menu).
 */
type P = SVGProps<SVGSVGElement> & { strokeWidth?: number };
const base = (props: P) => ({
  width: 20,
  height: 20,
  viewBox: "0 0 20 20",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "square" as const,
  strokeLinejoin: "miter" as const,
  "aria-hidden": true,
  ...props,
});

/** overview: the court from above, centre line and a goal area */
export const IconOverview = (p: P) => (
  <svg {...base(p)}>
    <path d="M2 4h16v12H2zM10 4v12" />
    <path d="M2 7.5c2.6 0 3.6 1.1 3.6 2.5S4.6 12.5 2 12.5" />
  </svg>
);
/** matches: a scoreboard with two numbers */
export const IconMatches = (p: P) => (
  <svg {...base(p)}>
    <path d="M2.5 5h15v10h-15zM10 5v10" />
    <path d="M5.5 8.5v3M13 8.5h2v3h-2z" />
  </svg>
);
/** team: a jersey */
export const IconTeam = (p: P) => (
  <svg {...base(p)}>
    <path d="M7 3 3 5.5l1.6 3.2L6 8v9h8V8l1.4.7L17 5.5 13 3c-.4 1.3-1.6 2-3 2s-2.6-.7-3-2Z" />
  </svg>
);
/** training: a cone */
export const IconTraining = (p: P) => (
  <svg {...base(p)}>
    <path d="M8.2 4h3.6l3.7 12h-11zM6.3 10.5h7.4M3 16h14" />
  </svg>
);
/** scenes: a frame with a play mark */
export const IconScenes = (p: P) => (
  <svg {...base(p)}>
    <path d="M2.5 4.5h15v11h-15z" />
    <path d="M8.5 7.5v5l4-2.5z" fill="currentColor" />
  </svg>
);
/** dates: a calendar sheet */
export const IconDates = (p: P) => (
  <svg {...base(p)}>
    <path d="M3 5h14v12H3zM3 8.5h14M7 3v3.5M13 3v3.5" />
    <path d="M6.5 12h2M11.5 12h2" />
  </svg>
);
/** goal: posts, crossbar and net */
export const IconGoal = (p: P) => (
  <svg {...base(p)}>
    <path d="M3 16V5h14v11" />
    <path d="M6 5v11M10 5v11M14 5v11M3 9h14M3 12.5h14" strokeWidth={0.9} />
  </svg>
);
/** ask the data: a question set on the court's 9 m arc */
export const IconAsk = (p: P) => (
  <svg {...base(p)}>
    <path d="M3 15c0-4.4 3.1-8 7-8s7 3.6 7 8" strokeDasharray="2 2" />
    <path d="M8.3 9.8c0-1 .8-1.8 1.8-1.8s1.8.7 1.8 1.6c0 1.3-1.8 1.4-1.8 2.7M10.1 14.5v.1" />
  </svg>
);

export const DEST_ICON: Record<Dest, (p: P) => React.JSX.Element> = {
  today: IconOverview,
  matches: IconMatches,
  team: IconTeam,
  training: IconTraining,
  scenes: IconScenes,
  dates: IconDates,
};

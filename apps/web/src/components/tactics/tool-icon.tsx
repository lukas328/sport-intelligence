import type { Side } from "@handball/tactics";
import type { Tool } from "./board";
import { BOARD_THEME } from "./board-theme";

/** The board's marks as small icons: the toolbar and the legend show what each line looks like. */
export function ToolIcon({ tool, className }: { tool: Tool; className?: string }) {
  const common = { fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  return (
    <svg aria-hidden viewBox="0 0 24 24" className={className ?? "size-5 shrink-0"}>
      {tool === "move" && (
        <>
          <circle cx={12} cy={12} r={5.5} fill={BOARD_THEME.own} stroke={BOARD_THEME.rim} strokeWidth={1.5} />
          <path d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3" {...common} />
        </>
      )}
      {tool === "run" && <path d="M3 19 L19 5 M13 5h6v6" {...common} />}
      {tool === "pass" && (
        <>
          <path d="M3 19 L17 7" {...common} strokeDasharray="3 3" />
          <path d="M13 5h6v6" {...common} />
        </>
      )}
      {tool === "dribble" && <path d="M3 19 l3-5 3 3 3-5 3 3 2.5-4 M14 5h5v5" {...common} />}
      {tool === "screen" && <path d="M3 19 L15 7 M11 3 L19 11" {...common} />}
      {tool === "ball" && <circle cx={12} cy={12} r={6} fill={BOARD_THEME.ball} stroke={BOARD_THEME.rim} strokeWidth={1.5} />}
    </svg>
  );
}

/** A player mark in the board's colours (legend). */
export function TokenDot({ side }: { side: Side }) {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className="size-5 shrink-0">
      <circle cx={12} cy={12} r={8} fill={side === "own" ? BOARD_THEME.own : BOARD_THEME.opp} stroke={BOARD_THEME.rim} strokeWidth={1.5} />
    </svg>
  );
}

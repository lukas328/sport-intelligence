import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** Home : away with the score as the loudest element of the page. */
export function Scoreboard({
  home,
  away,
  homeScore,
  awayScore,
  halftime,
  ownSide,
  vsLabel = "vs",
  className,
}: {
  home: ReactNode;
  away: ReactNode;
  homeScore: number | null;
  awayScore: number | null;
  halftime?: string | null;
  ownSide: "home" | "away" | null;
  /** shown instead of a score before the match */
  vsLabel?: string;
  className?: string;
}) {
  const scored = homeScore != null && awayScore != null;
  const name = (n: ReactNode, own: boolean, align: "left" | "right") => (
    <span className={cn("min-w-0 flex-1 text-lg font-bold leading-tight font-wide sm:text-2xl", align === "right" && "text-right", !own && "text-muted")}>{n}</span>
  );
  return (
    <div className={cn("flex items-center gap-3 sm:gap-6", className)}>
      {name(home, ownSide === "home", "right")}
      <div className="shrink-0 text-center">
        {scored ? (
          <p className="font-score text-4xl leading-none sm:text-6xl" data-testid="score">
            {homeScore}:{awayScore}
          </p>
        ) : (
          <p className="eyebrow !text-sm">{vsLabel}</p>
        )}
        {halftime && <p className="mt-1.5 text-xs font-medium text-muted tabular-nums">({halftime})</p>}
      </div>
      {name(away, ownSide === "away", "left")}
    </div>
  );
}

/** Jersey number as a small badge, the way coaches name players. */
export function Jersey({ n, className }: { n: number | null | undefined; className?: string }) {
  return (
    <span className={cn("inline-grid min-w-7 place-items-center rounded-md bg-foreground px-1 py-0.5 text-xs font-bold text-background font-wide tabular-nums", className)}>
      {n ?? "–"}
    </span>
  );
}

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { CourtLines } from "./court-lines";

/**
 * The stage: the club colour as a full-bleed surface with the court as its frame. At most one per
 * screen, always at the top, only on overview, season and match (docs/DESIGN.md, "Bühne").
 *
 * On wide screens (from 1280 px) the court covers the right 58 % of the band, so its goal area (6/14 of that) is
 * where the `aside` (the score) stands; the text keeps clear of the dashed 9 m line. On narrow
 * screens the court is hidden and the aside comes first, above the headline.
 */
export function Stage({ children, aside, compact, className }: { children: ReactNode; aside?: ReactNode; compact?: boolean; className?: string }) {
  return (
    <section className={cn("bleed relative -mt-5 overflow-hidden bg-club text-club-ink lg:-mt-10", className)}>
      {!compact && <CourtLines className="absolute inset-y-0 right-0 hidden h-full w-[58%] xl:block" />}
      {aside && <div className={cn("absolute inset-y-0 right-0 hidden items-center xl:flex", compact ? "pr-[max(2.5rem,calc((100%-1240px)/2+2.5rem))]" : "w-[24.8%] justify-center")}>{aside}</div>}
      <div className={cn("relative mx-auto max-w-[1240px] px-4 sm:px-6 lg:px-10", compact ? "py-6 lg:py-7" : "pt-8 pb-9 lg:pt-12 lg:pb-14")}>
        {aside && <div className="mb-6 xl:hidden">{aside}</div>}
        <div className={cn("min-w-0", aside ? "max-w-2xl xl:max-w-[min(42rem,calc(42vw-8rem))]" : "max-w-2xl")}>{children}</div>
      </div>
    </section>
  );
}

/** Buttons on the stage: solid in the stage's ink, or outlined. */
export const stageButton = (variant: "solid" | "outline" = "solid") =>
  cn(
    "inline-flex min-h-11 items-center gap-2 rounded-md px-5 text-[0.9375rem] font-semibold transition-[filter,background] duration-150 [&_svg]:size-4",
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-current",
    variant === "solid" ? "bg-club-ink text-club hover:brightness-95" : "ring-2 ring-inset ring-current/60 hover:bg-club-ink/10",
  );

/** Small label on the stage (demo data, estimates): outlined in the stage ink. */
export function StageTag({ children }: { children: ReactNode }) {
  return <span className="inline-flex items-center rounded-sm px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ring-current/50">{children}</span>;
}

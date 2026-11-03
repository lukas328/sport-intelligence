import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { CourtLines } from "./court-lines";

/**
 * The stage: the club colour as a full-bleed surface with the court as its frame. At most one per
 * screen, always at the top, only on overview, season and match (docs/DESIGN.md, "Bühne").
 */
export function Stage({ children, aside, compact, className }: { children: ReactNode; aside?: ReactNode; compact?: boolean; className?: string }) {
  return (
    <section className={cn("bleed relative -mt-5 overflow-hidden bg-club text-club-ink lg:-mt-10", className)}>
      <CourtLines className="absolute inset-y-0 right-0 hidden h-full w-[46rem] md:block" />
      <div
        className={cn(
          "relative mx-auto flex max-w-[1240px] flex-col gap-8 px-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-10",
          compact ? "py-6 lg:py-7" : "pt-8 pb-9 lg:pt-12 lg:pb-14",
        )}
      >
        <div className="min-w-0 max-w-2xl">{children}</div>
        {aside && <div className="shrink-0 lg:pr-[3.5rem]">{aside}</div>}
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

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { CourtLines } from "./court-lines";

/**
 * The stage: the club colour as a full-bleed surface with the court as its frame. At most one per
 * screen, always at the top, only on overview, season and match (docs/DESIGN.md, "Bühne").
 *
 * From 1280 px the court is a square at the right edge and the `aside` (usually the score) stands
 * in its goal area; the text keeps clear of the dashed 9 m line. Below that the court is hidden
 * and the aside follows the text.
 */
export function Stage({
  children,
  eyebrow,
  aside,
  compact,
  full,
  pullMobile = true,
  className,
}: {
  children: ReactNode;
  /** first line (greeting, date); on phones the aside follows it, before the headline */
  eyebrow?: ReactNode;
  aside?: ReactNode;
  compact?: boolean;
  full?: boolean;
  /** pull the band up to the top bar on phones (off when something sits above it) */
  pullMobile?: boolean;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "relative overflow-hidden bg-club text-club-ink",
        full ? "bleed-full -mt-6 sm:-mt-10" : cn("bleed lg:-mt-10", pullMobile && "-mt-5"),
        className,
      )}
    >
      {!compact && (
        // the court sits as a square at the right edge; its goal area (6 of 14 m) holds the aside
        <div className="absolute inset-y-0 right-0 hidden aspect-square h-full xl:block">
          <CourtLines className="absolute inset-0 size-full" />
          {aside && <div className="absolute inset-y-0 right-0 flex w-[43%] items-center justify-center">{aside}</div>}
        </div>
      )}
      {compact && aside && <div className="absolute inset-y-0 right-0 hidden items-center pr-[max(2.5rem,calc((100%-1240px)/2+2.5rem))] xl:flex">{aside}</div>}
      <div className={cn("relative mx-auto max-w-[1240px] px-4 sm:px-6 lg:px-10", compact ? "py-6 lg:py-7" : "pt-7 pb-8 lg:pt-12 lg:pb-14")}>
        <div className={cn("min-w-0", aside ? "max-w-2xl xl:max-w-[min(42rem,calc(100%-min(100dvh,36rem)))]" : "max-w-2xl")}>
          {eyebrow && <p className="text-[0.9375rem] font-semibold">{eyebrow}</p>}
          {aside && <div className="mt-5 mb-2 xl:hidden">{aside}</div>}
          {children}
        </div>
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

/** A quiet text action on the stage, next to the buttons. */
export const stageLink = "inline-flex min-h-11 items-center gap-2 px-1 text-[0.9375rem] font-semibold underline-offset-4 hover:underline [&_svg]:size-4";

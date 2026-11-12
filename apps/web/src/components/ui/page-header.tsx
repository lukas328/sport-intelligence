import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Seitenkopf (Anlauf): the head of every page without a match. A small kick line, the slanted
 * title, at most one primary action, and the Keil: the slanted lower edge in the club colour,
 * across the whole width. No description under the title: the title says it, the kick gives the
 * context. One per route (design-lint.test.ts).
 */
export function PageHeader({ eyebrow, title, actions, figure, figureLabel, className }: { eyebrow?: ReactNode; title: ReactNode; actions?: ReactNode; figure?: ReactNode; figureLabel?: ReactNode; className?: string }) {
  return (
    <header data-zone="kopf" className={cn("bleed-x relative mb-6 px-4 pb-[30px] md:mb-8 md:px-8 md:pb-10", className)}>
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
        <div className="min-w-0">
          {eyebrow && <p className="mb-1.5 text-[13px] font-semibold text-ink-2 md:mb-2.5 md:text-[15px]">{eyebrow}</p>}
          <h1 className="max-w-[920px] text-[34px] leading-[.96] md:text-[58px]">{title}</h1>
        </div>
        {figure != null && (
          <div className="flex items-baseline gap-2.5 md:block md:text-right">
            <b className="font-num block text-[52px] leading-[.8] text-club-text md:text-[96px]">{figure}</b>
            {figureLabel && <span className="text-[15px] font-semibold text-ink-2">{figureLabel}</span>}
          </div>
        )}
        {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
      </div>
      <span
        aria-hidden
        data-keil=""
        className="absolute right-0 bottom-0 left-0 h-3.5 bg-club shadow-[inset_0_0_0_1.5px_var(--club-edge)] [clip-path:polygon(0_0,100%_78%,100%_100%,0_100%)] md:h-[22px]"
      />
    </header>
  );
}

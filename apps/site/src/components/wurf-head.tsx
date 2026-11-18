import type { ReactNode } from "react";
import { Flight, type FlightLabels, type ReportGoal } from "@/components/anlauf/charts";
import { cn } from "@/lib/cn";
import { HTML_LANG, fmt, messages, type Locale } from "@/lib/i18n";

/** The result: our goals, theirs underlined in the opponent's colour (no echo copies, BEFUNDE-3 U27). */
export function Score({ own, opp, label, className }: { own: number; opp: number; label: string; className?: string }) {
  return (
    <div className={cn("font-num relative whitespace-nowrap", className)} style={{ lineHeight: 0.8 }} role="img" aria-label={label}>
      <span aria-hidden className="relative block">
        {own}:<u className="decoration-opp [text-decoration-skip-ink:none] [text-decoration-thickness:.045em] [text-underline-offset:.06em]">{opp}</u>
      </span>
    </div>
  );
}

/**
 * Wurf: the result head (club colour, lower edge cut at a slant, slanted title, the result large,
 * the run of the match as a line). On the website it carries the product sentence as well.
 */
export function WurfHead({
  kick,
  title,
  lead,
  own,
  opp,
  ownName,
  oppName,
  scoreLabel,
  goals,
  flightLabels,
  titleAs = "h1",
  scoreNote,
  children,
}: {
  kick?: ReactNode;
  title: ReactNode;
  lead?: ReactNode;
  own: number;
  opp: number;
  ownName: string;
  oppName: string;
  scoreLabel: string;
  goals: readonly ReportGoal[];
  flightLabels: FlightLabels;
  titleAs?: "h1" | "h2";
  /** over the score: says the example match is made up (start page) */
  scoreNote?: ReactNode;
  /** under the lead: the team field on the start page */
  children?: ReactNode;
}) {
  const T = titleAs;
  return (
    <header
      data-zone="wurf"
      className="on-club relative grid grid-cols-1 bg-club px-4 pt-6 pb-[4.5rem] text-club-ink shadow-[inset_0_0_0_2px_var(--club-edge)] [clip-path:polygon(0_0,100%_0,100%_93%,0_100%)] md:grid-cols-[minmax(0,1fr)_minmax(0,34rem)] md:gap-8 md:px-8 md:pt-10 md:pb-[6.5rem] md:[clip-path:polygon(0_0,100%_0,100%_calc(100%-6rem),0_100%)] lg:px-[max(2rem,calc((100vw-var(--wrap))/2+2rem))]"
    >
      <div className="min-w-0">
        {kick && <p className="mb-3 text-base font-semibold md:mb-4 md:text-[1.0625rem]">{kick}</p>}
        <T className="text-[2.5rem] leading-[.96] md:text-[clamp(4.25rem,2.4rem+2.4vw,6rem)]">{title}</T>
        {lead && <p className="mt-4 max-w-[34rem] text-[1.125rem] leading-normal font-medium md:mt-6 md:text-[clamp(1.375rem,1rem+0.45vw,1.625rem)] min-[100rem]:max-w-[38rem]">{lead}</p>}
        {children && <div className="mt-6 md:mt-8">{children}</div>}
      </div>
      <div className="mt-6 flex min-w-0 flex-col md:mt-0">
        {scoreNote && <p className="mb-2 text-base font-semibold md:text-right md:text-[1.0625rem]">{scoreNote}</p>}
        <p className="upright flex flex-wrap gap-x-6 gap-y-1 text-base md:justify-end md:text-[1.0625rem]" aria-hidden>
          <span>{ownName}</span>
          <span>
            <i className="mr-2 inline-block size-3.5 bg-opp align-[-1px] shadow-[0_0_0_1.5px_var(--club-ink)]" />
            {oppName}
          </span>
        </p>
        <Score own={own} opp={opp} label={scoreLabel} className="mt-3 text-[min(6.5rem,25vw)] md:text-right md:text-[min(12rem,16vw)]" />
        <Flight goals={goals} width={390} height={90} className="-mx-4 mt-6 w-[calc(100%+2rem)] md:hidden" />
      </div>
      {/* the run of the match under the text, in the flow with its own row, so it never runs
          through the lead at any width (BEFUNDE-4 U43) */}
      <Flight goals={goals} width={1000} height={120} labels={flightLabels} slant={48} className="mt-10 hidden w-full md:col-span-2 md:block" />
    </header>
  );
}

/**
 * Seitenkopf: pages without a match (BEFUNDE-3 U9). Kick line with a slanted band in the club
 * colour, the slanted title, the lead; on the right (under the lead on the phone) a picture of
 * what the page holds, its `aside` (the four steps, the topics, «30 Tage gratis», the search, …).
 * Underneath the Keil, the slanted edge of the Wurf head, as a firm wedge in the club colour. The
 * title grows with a wide screen (U4). The «Stand» date is not here: it stands small under the
 * content where a page has a real one (`Updated`, U26).
 */
export function PageHead({ kick, title, lead, aside, children }: { kick?: ReactNode; title: ReactNode; lead?: ReactNode; aside?: ReactNode; children?: ReactNode }) {
  return (
    <header data-zone="kopf" className="relative pt-6 pb-16 md:pt-10 md:pb-24">
      <div
        className={cn(
          "wrap grid grid-cols-1 gap-y-8",
          aside != null && "lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)] lg:items-center lg:gap-x-14 min-[100rem]:grid-cols-[minmax(0,1fr)_minmax(0,30rem)]",
        )}
      >
        <div className="min-w-0">
          {kick && (
            <div className="mb-3 flex flex-wrap items-center gap-x-3 text-[1.0625rem] font-semibold text-ink-2 md:mb-4">
              {typeof kick === "string" && <i aria-hidden className="mark-band h-2.5 w-8 shrink-0" />}
              {kick}
            </div>
          )}
          <h1 className="max-w-[52rem] text-[2.5rem] leading-[.96] md:text-[clamp(3.5rem,2rem+2.4vw,5.25rem)]">{title}</h1>
          {lead && <p className="mt-5 max-w-[40rem] text-[1.1875rem] text-ink-2 md:text-[1.3125rem]">{lead}</p>}
          {children}
        </div>
        {aside != null && <div className="min-w-0">{aside}</div>}
      </div>
      <span
        aria-hidden
        data-keil=""
        className="absolute right-0 bottom-0 left-0 h-6 bg-club shadow-[inset_0_0_0_1.5px_var(--club-edge)] [clip-path:polygon(0_0,100%_62%,100%_100%,0_100%)] md:h-10"
      />
    </header>
  );
}

/**
 * «Stand: 17. November 2026»: the day a page was last reviewed, small under its content (U26).
 * Only pages with a date of their own carry it (lib/site.ts PAGE_UPDATED, a guide's `updated`).
 */
export function Updated({ locale, date }: { locale: Locale; date: string }) {
  const text = new Intl.DateTimeFormat(HTML_LANG[locale], { dateStyle: "long", timeZone: "Europe/Zurich" }).format(new Date(date));
  return (
    <p className="mt-16 text-base text-ink-2">
      <time dateTime={date}>{fmt(messages(locale).guides.updated, { date: text })}</time>
    </p>
  );
}

/** Section head: slanted title over a 2 px ink rule, optional note at the right. */
export function SectionHead({ id, title, note, as = "h2" }: { id?: string; title: ReactNode; note?: ReactNode; as?: "h2" | "h3" }) {
  const T = as;
  return (
    <div className="section-head flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
      <T id={id} className={as === "h2" ? "text-[1.875rem] md:text-[2.375rem]" : "text-[1.375rem] md:text-[1.5rem]"}>
        {title}
      </T>
      {note && <span className="text-[1.0625rem] text-ink-2">{note}</span>}
    </div>
  );
}

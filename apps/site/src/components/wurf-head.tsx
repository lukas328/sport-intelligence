import type { ReactNode } from "react";
import { Flight, type FlightLabels, type ReportGoal } from "@/components/anlauf/charts";
import { cn } from "@/lib/cn";
import { HTML_LANG, fmt, messages, type Locale } from "@/lib/i18n";
import { SITE_UPDATED } from "@/lib/site";

/** The result: our goals, theirs underlined in the opponent's colour; two offset outlines behind. */
export function Score({ own, opp, label, className }: { own: number; opp: number; label: string; className?: string }) {
  return (
    <div className={cn("font-num relative whitespace-nowrap", className)} style={{ lineHeight: 0.8 }} role="img" aria-label={label}>
      <span aria-hidden className="score-echo absolute top-0 right-0 opacity-[.22] [transform:translate(-.2em,-.04em)] max-md:right-auto max-md:left-0 max-md:[transform:translate(.2em,-.06em)]">
        {own}:{opp}
      </span>
      <span aria-hidden className="score-echo absolute top-0 right-0 opacity-[.42] [transform:translate(-.1em,-.02em)] max-md:right-auto max-md:left-0 max-md:[transform:translate(.1em,-.03em)]">
        {own}:{opp}
      </span>
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
  children,
}: {
  kick: ReactNode;
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
  /** under the lead: the team field on the start page */
  children?: ReactNode;
}) {
  const T = titleAs;
  return (
    <header
      data-zone="wurf"
      className="on-club relative grid grid-cols-1 bg-club px-4 pt-6 pb-[4.5rem] text-club-ink shadow-[inset_0_0_0_2px_var(--club-edge)] [clip-path:polygon(0_0,100%_0,100%_93%,0_100%)] md:grid-cols-[minmax(0,1fr)_minmax(0,34rem)] md:gap-8 md:px-8 md:pt-10 md:pb-[11rem] md:[clip-path:polygon(0_0,100%_0,100%_calc(100%-6rem),0_100%)] lg:px-[max(2rem,calc((100vw-76rem)/2+2rem))]"
    >
      <div className="min-w-0">
        <p className="mb-3 text-base font-semibold md:mb-4 md:text-[1.0625rem]">{kick}</p>
        <T className="text-[2.5rem] leading-[.96] md:text-[4.25rem]">{title}</T>
        {lead && <p className="mt-4 max-w-[34rem] text-[1.125rem] leading-normal font-medium md:mt-6 md:text-[1.375rem]">{lead}</p>}
        {children && <div className="mt-6 md:mt-8">{children}</div>}
      </div>
      <div className="mt-6 flex min-w-0 flex-col md:mt-0">
        <p className="font-slant flex flex-wrap gap-x-6 gap-y-1 text-base md:justify-end md:text-[1.0625rem]" aria-hidden>
          <span>{ownName}</span>
          <span>
            <i className="mr-2 inline-block size-3.5 bg-opp align-[-1px] shadow-[0_0_0_1.5px_var(--club-ink)]" />
            {oppName}
          </span>
        </p>
        <Score own={own} opp={opp} label={scoreLabel} className="mt-3 text-[min(6.5rem,25vw)] md:text-right md:text-[min(12rem,16vw)]" />
        <Flight goals={goals} width={390} height={90} className="-mx-4 mt-6 w-[calc(100%+2rem)] md:hidden" />
      </div>
      <Flight goals={goals} width={1000} height={120} labels={flightLabels} slant={48} className="absolute right-0 bottom-[2.5rem] left-0 hidden w-full md:block" />
    </header>
  );
}

/**
 * Seitenkopf: pages without a match. Kick line, slanted title on the cloth, the Keil (the slanted
 * edge of the Wurf head as a wedge) underneath in the club colour.
 */
export function PageHead({ kick, title, lead, figure, figureLabel, children }: { kick?: ReactNode; title: ReactNode; lead?: ReactNode; figure?: ReactNode; figureLabel?: ReactNode; children?: ReactNode }) {
  return (
    <header data-zone="kopf" className="relative pt-8 pb-10 md:pt-14 md:pb-14">
      <div className="wrap relative">
        {kick && <p className="mb-2 text-[1.0625rem] font-semibold text-ink-2 md:mb-3">{kick}</p>}
        <h1 className="max-w-[52rem] text-[2.5rem] leading-[.96] md:text-[4rem]">{title}</h1>
        {figure != null && (
          <p className="mt-4 flex items-baseline gap-3 md:absolute md:top-0 md:right-8 md:mt-0 md:block md:text-right">
            <b className="font-num block text-[4rem] leading-[.8] text-club-text md:text-[7rem]">{figure}</b>
            {figureLabel && <span className="text-[1.0625rem] font-semibold text-ink-2 md:mt-2 md:block">{figureLabel}</span>}
          </p>
        )}
        {lead && <p className="mt-5 max-w-[40rem] text-[1.1875rem] text-ink-2 md:text-[1.3125rem]">{lead}</p>}
        {children}
      </div>
      <span
        aria-hidden
        data-keil=""
        className="absolute right-0 bottom-0 left-0 h-3.5 bg-club shadow-[inset_0_0_0_1.5px_var(--club-edge)] [clip-path:polygon(0_0,100%_78%,100%_100%,0_100%)] md:h-[22px]"
      />
    </header>
  );
}

/** «Stand: 13. November 2026»: the date of the last review of a page, visible under the lead. */
export function Updated({ locale, date = SITE_UPDATED }: { locale: Locale; date?: string }) {
  const text = new Intl.DateTimeFormat(HTML_LANG[locale], { dateStyle: "long", timeZone: "Europe/Zurich" }).format(new Date(date));
  return (
    <p className="mt-5 text-[1.0625rem] text-ink-2">
      <time dateTime={date}>{fmt(messages(locale).guides.updated, { date: text })}</time>
    </p>
  );
}

/** Section head: slanted title over a 2 px ink rule, optional note at the right. */
export function SectionHead({ id, title, note, as = "h2" }: { id?: string; title: ReactNode; note?: ReactNode; as?: "h2" | "h3" }) {
  const T = as;
  return (
    <div className="section-head flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
      <T id={id} className={as === "h2" ? "text-[1.875rem] md:text-[2.375rem]" : "font-slant text-[1.5rem] md:text-[1.75rem]"}>
        {title}
      </T>
      {note && <span className="text-[1.0625rem] text-ink-2">{note}</span>}
    </div>
  );
}

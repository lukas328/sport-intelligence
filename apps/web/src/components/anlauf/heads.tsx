import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Flight, type FlightLabels, type ReportGoal } from "./charts";

/**
 * The three heads of the Anlauf look. Per route there is one Wurf head or one Streifen
 * (matches), or one Seitenkopf with the Keil (everything else). The club colour as an area only
 * here (and in the active marker, own lines and numerals).
 */

/** A club name that may break after «/» («SG Wädenswil/<wbr>Horgen»), for large text (UX test N11). */
export function Breakable({ text }: { text: string }) {
  const parts = text.split("/");
  return (
    <>
      {parts.map((part, i) => (
        <span key={i}>
          {part}
          {i < parts.length - 1 && (
            <>
              /<wbr />
            </>
          )}
        </span>
      ))}
    </>
  );
}

/** The result: our goals, theirs underlined in the opponent's colour; two offset outlines behind. */
export function Score({
  own,
  opp,
  outlines = 2,
  phoneLeft = false,
  className,
  pending,
}: {
  own: number | null;
  opp: number | null;
  outlines?: 0 | 1 | 2;
  /** before the game: date and time in place of a «-:-» placeholder (UX test B42) */
  pending?: ReactNode;
  /** left-aligned on the phone: the outlines step to the right */
  phoneLeft?: boolean;
  className?: string;
}) {
  const text = own == null || opp == null ? "-:-" : null;
  if (text && pending) {
    return (
      <div className={cn("font-num whitespace-nowrap", className)} style={{ lineHeight: 0.9 }} data-testid="score-pending">
        <span className="block text-[0.36em]">{pending}</span>
      </div>
    );
  }
  // no result (yet, or while it loads): the place stays empty, not a block of «-:-» (UX test A09)
  if (text) return <div aria-hidden className={cn("font-num invisible whitespace-nowrap", className)} style={{ lineHeight: 0.8 }} data-testid="score-empty">0:0</div>;
  const body = text ?? (
    <>
      {own}:<u className="decoration-opp [text-decoration-skip-ink:none] [text-decoration-thickness:.045em] [text-underline-offset:.06em]">{opp}</u>
    </>
  );
  return (
    // line height inline: tailwind-merge drops a leading class when a size class follows
    <div className={cn("font-num relative whitespace-nowrap", className)} style={{ lineHeight: 0.8 }}>
      {outlines >= 2 && (
        <span aria-hidden className={cn("score-echo absolute top-0 right-0 opacity-[.22] [transform:translate(-.2em,-.04em)]", phoneLeft && "max-md:right-auto max-md:left-0 max-md:[transform:translate(.2em,-.06em)]")}>
          {text ?? `${own}:${opp}`}
        </span>
      )}
      {outlines >= 1 && (
        <span aria-hidden className={cn("score-echo absolute top-0 right-0 opacity-[.42] [transform:translate(-.1em,-.02em)]", phoneLeft && "max-md:right-auto max-md:left-0 max-md:[transform:translate(.1em,-.03em)]")}>
          {text ?? `${own}:${opp}`}
        </span>
      )}
      <span className="relative block">{body}</span>
    </div>
  );
}

/** Small square in the opponent's colour (with an edge in the ink on the club colour). */
export function OppChip({ className }: { className?: string }) {
  return <i aria-hidden className={cn("inline-block size-3 bg-opp align-[-1px] shadow-[0_0_0_1.5px_var(--club-ink)]", className)} />;
}

/**
 * Wurf: the result head of the start and of the tab Spiel. Club colour, lower edge slanted,
 * slanted title, the result large, the run of the match as a line underneath.
 */
export function WurfHead({
  kick,
  title,
  own,
  opp,
  ownName,
  oppName,
  goals,
  flightLabels,
  meta,
  children,
  waiting = false,
  pending,
  span,
  scoreNote,
}: {
  kick?: ReactNode;
  title: ReactNode;
  own: number | null;
  opp: number | null;
  ownName: string;
  oppName: string;
  /** the goal sequence of the report; without it, no line */
  goals?: readonly ReportGoal[] | null;
  flightLabels?: FlightLabels;
  meta?: ReactNode;
  children?: ReactNode;
  /** before the first result: no club area, an ink outline instead */
  waiting?: boolean;
  pending?: ReactNode;
  /** the match minutes a video covers: the line runs over them only, without halftime labels */
  span?: readonly [number, number] | null;
  /** a word under the result when it is not the match's own («Tore im Video») */
  scoreNote?: ReactNode;
}) {
  const from = span ? span[0] : 0;
  const length = span ? span[1] : 60;
  return (
    <header
      data-zone="wurf"
      className={cn(
        "relative grid grid-cols-1 px-4 pt-5 [clip-path:polygon(0_0,100%_0,100%_88%,0_100%)] md:grid-cols-[minmax(0,1fr)_minmax(0,560px)] md:gap-6 md:px-8 md:pt-9 md:[clip-path:polygon(0_0,100%_0,100%_80%,0_100%)]",
        // without a goal sequence there is no line: the slant follows right under title and score
        goals && goals.length > 0 ? "min-h-[400px] md:h-[410px]" : "pb-14 md:pb-20",
        waiting ? "bg-transparent text-ink shadow-[inset_0_0_0_2px_var(--ink)]" : "bg-club text-club-ink shadow-[inset_0_0_0_2px_var(--club-edge)]",
      )}
    >
      {/* above the drawn line: the controls in the head stay reachable */}
      <div className="relative z-10 min-w-0">
        {kick && <p className="mb-2 text-[15px] font-semibold md:mb-3.5 md:text-[15px]">{kick}</p>}
        {/* long club names («SG Wädenswil/Horgen») wrap instead of running out (UX test N11) */}
        <h1 className="text-[32px] leading-[.96] [overflow-wrap:break-word] md:text-[58px]">{title}</h1>
        {meta && <div className="mt-[18px] text-sm font-semibold">{meta}</div>}
        {children}
      </div>
      <div className="flex min-w-0 flex-col">
        <Score own={own} opp={opp} pending={pending} phoneLeft className="mt-[18px] text-[100px] md:mt-1 md:text-right md:text-[196px]" />
        {scoreNote && (
          // on a wide screen above the score: under it the drawn course covered it (real-video
          // test, second round, 1280 px)
          <p className="mt-1 text-[15px] font-semibold md:order-[-1] md:mt-0 md:text-right" data-testid="score-note">
            {scoreNote}
          </p>
        )}
        <p className="font-slant mt-2 flex flex-wrap gap-[18px] text-[15px] md:order-first md:mt-0 md:mb-3.5 md:justify-end md:gap-7 md:text-[15px]">
          <span>{ownName}</span>
          <span>
            <OppChip className="mr-2" />
            {oppName}
          </span>
        </p>
        {goals && goals.length > 0 && <Flight goals={goals} width={390} height={90} from={from} length={length} className="-mx-4 mt-3 mb-14 w-[calc(100%+2rem)] md:hidden" />}
      </div>
      {goals && goals.length > 0 && (
        <>
          <Flight goals={goals} width={1000} height={120} labels={span ? undefined : flightLabels} from={from} length={length} slant={48} className="pointer-events-none absolute right-0 bottom-[30px] left-0 hidden w-full md:block" />

        </>
      )}
    </header>
  );
}

/** Streifen: the slim head of every sub-page of a match (Video, Zahlen, Prüfen, Spieltag). */
export function Strip({ name, sub, own, opp, children, live, pending }: { name: ReactNode; sub?: ReactNode; own: number | null; opp: number | null; children?: ReactNode; live?: boolean; pending?: ReactNode }) {
  return (
    <header
      data-zone="strip"
      className={cn(
        // with large text the score goes under the name instead of over it (UX test N11)
        "relative flex flex-wrap items-start justify-between gap-x-4 gap-y-1 bg-club px-4 pt-3.5 pb-8 text-club-ink shadow-[inset_0_0_0_2px_var(--club-edge)] [clip-path:polygon(0_0,100%_0,100%_72%,0_100%)] md:px-8 md:pt-5",
        live ? "min-h-[168px]" : "min-h-[104px] md:min-h-[124px]",
      )}
    >
      <div className="font-slant min-w-0 flex-1 basis-[12ch] text-[17px] leading-[1.05] [overflow-wrap:anywhere] md:text-2xl">
        {name}
        {sub && <small className="mt-1.5 block font-sans text-xs font-medium not-italic md:text-[15px]">{sub}</small>}
        {children}
      </div>
      <Score own={own} opp={opp} pending={pending} outlines={1} className="text-[48px] md:text-[72px]" />
    </header>
  );
}

/**
 * Seitenkopf: pages without a match. No area of colour, only the slanted lower edge of the
 * Wurf head as a wedge (Keil) in the club colour. `figure` is one big numeral at the right.
 */
export function PageHead({ kick, title, figure, figureLabel, actions }: { kick?: ReactNode; title: ReactNode; figure?: ReactNode; figureLabel?: ReactNode; actions?: ReactNode }) {
  return (
    <header data-zone="kopf" className="relative mb-6 px-4 pt-5 pb-[30px] md:mb-8 md:px-8 md:pt-[30px] md:pb-10">
      {kick && <p className="mb-1.5 text-[15px] font-semibold text-ink-2 md:mb-2.5 md:text-[15px]">{kick}</p>}
      <h1 className="max-w-[920px] text-[34px] leading-[.96] md:text-[58px]">{title}</h1>
      {figure != null && (
        <div className="mt-3 flex items-baseline gap-2.5 md:absolute md:top-[26px] md:right-8 md:mt-0 md:block md:text-right">
          <b className="font-num text-[52px] leading-[.8] text-club-text md:block md:text-[96px]">{figure}</b>
          {figureLabel && <span className="text-[15px] font-semibold text-ink-2">{figureLabel}</span>}
        </div>
      )}
      {actions && <div className="mt-5 flex flex-wrap gap-3">{actions}</div>}
      <span
        aria-hidden
        data-keil=""
        className="absolute right-0 bottom-0 left-0 h-3.5 bg-club shadow-[inset_0_0_0_1.5px_var(--club-edge)] [clip-path:polygon(0_0,100%_78%,100%_100%,0_100%)] md:h-[22px]"
      />
    </header>
  );
}

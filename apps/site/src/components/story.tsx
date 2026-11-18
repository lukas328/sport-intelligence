/**
 * The pieces of the start page's week (lib/story.ts): the time stamp over each part, the evening
 * after the defeat and the right wing before and after (the team chat: components/phone-chat.tsx).
 */
import type { ReactNode } from "react";
import { HalfCourtLines } from "@/components/anlauf/court";
import { HALF_BOX } from "@/components/anlauf/geometry";
import { cn } from "@/lib/cn";
import { fmt } from "@/lib/i18n";
import type { StoryCourt } from "@/lib/story";
import type { Messages } from "@/messages/de";

/**
 * «Samstag, 19 Uhr»: the time stamp over a part of the week, after a short band in the club
 * colour (on the club colour itself the band is white).
 */
export function When({ children, dark = false, onClub = false }: { children: ReactNode; dark?: boolean; onClub?: boolean }) {
  return (
    <p className={cn("flex items-center gap-3 font-mono text-base font-semibold tracking-wide uppercase md:text-[1.0625rem]", onClub ? "text-club-ink" : dark ? "text-[#dcdfe2]" : "text-ink")}>
      <i aria-hidden className={cn("inline-block h-2 w-10 shrink-0", onClub ? "-skew-x-[14deg] bg-club-ink" : "mark-band")} />
      {children}
    </p>
  );
}

/** Saturday, 7 pm: the score, the feeling and the video nobody watches (W25). */
export function Evening({ t, score }: { t: Messages["home"]["problemCard"]; score: string }) {
  return (
    <div role="img" aria-label={fmt(t.label, { score })} className="border-2 border-[#3a3d42] bg-[#1f2125] p-6 md:p-8">
      <div aria-hidden>
        <p className="flex flex-wrap items-baseline gap-x-4">
          <b className="font-num text-[4.5rem] leading-[.85] text-ground md:text-[6rem]">{score}</b>
          <span className="text-[1.125rem] font-semibold text-[#dcdfe2]">{t.result}</span>
        </p>
        <div className="mt-7 border-t border-[#3a3d42] pt-5">
          <p className="text-base font-semibold text-[#b9bec4]">{t.feelingTitle}</p>
          <p className="mt-1 text-[1.375rem] leading-snug font-semibold text-ground md:text-[1.5rem]">{t.feeling}</p>
        </div>
        <div className="mt-6 border-t border-[#3a3d42] pt-5">
          <p className="text-base font-semibold text-[#b9bec4]">{t.videoTitle}</p>
          {/* a player bar that never moved: the playhead at 0:00 of 60:00. When the card comes in,
              the playhead twitches as if it would start, stays, and then «nie angeschaut» (S8) */}
          <div className="mt-3 flex items-center gap-3 font-mono text-base text-[#dcdfe2]">
            <svg viewBox="0 0 20 20" className="size-6 shrink-0">
              <path d="M5 3l12 7-12 7z" fill="currentColor" />
            </svg>
            <span>0:00</span>
            <span className="relative h-1.5 flex-1 bg-[#3a3d42]">
              <i className="nudge absolute -top-[5px] left-0 size-4 bg-ground" style={{ borderRadius: "50%" }} />
            </span>
            <span>60:00</span>
          </div>
          <p className="late mt-2 text-[1.0625rem] text-[#dcdfe2]">{t.video}</p>
        </div>
      </div>
    </div>
  );
}

/** One half court with the goals conceded as dots: the right wing in ink, the rest faint. */
export function Court({ court, label }: { court: StoryCourt; label: string }) {
  const k = 300 / HALF_BOX[2];
  return (
    <svg viewBox={HALF_BOX.join(" ")} role="img" aria-label={label} className="block w-full">
      <HalfCourtLines />
      {/* the right wing, where it happened: a yellow field behind the dots (with a word next to it) */}
      <path d="M15.4 0H20V5.2H17.8Z" fill="var(--attn)" opacity={0.55} />
      {court.dots
        .filter((d) => !d.ra)
        .map((d, i) => (
          <circle key={`o${i}`} cx={d.at[0]} cy={d.at[1]} r={3.6 / k} fill="var(--ground)" stroke="var(--ink)" strokeOpacity={0.45} strokeWidth={1.2} vectorEffect="non-scaling-stroke" />
        ))}
      {court.dots
        .filter((d) => d.ra)
        .map((d, i) => (
          <circle key={`r${i}`} cx={d.at[0]} cy={d.at[1]} r={4.6 / k} fill="var(--ink)" />
        ))}
    </svg>
  );
}

/**
 * Three matches later: the right wing before and after, as the season would show it (W27), big
 * and side by side on the club colour (S12). The numbers stand as they are at once, no counting (BEFUNDE-3 U20).
 */
export function BeforeAfter({ t, before, after, zone }: { t: Messages["home"]; before: StoryCourt; after: StoryCourt; zone: string }) {
  const side = (c: StoryCourt, when: string, strong: boolean) => (
    <figure className="m-0 grid min-w-0 grid-cols-1 items-end gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,17rem)] lg:gap-6">
      <figcaption className="min-w-0">
        <span className="block font-mono text-base font-semibold tracking-wide uppercase max-lg:min-h-[2lh] md:text-[1.0625rem]">{when}</span>
        <span className="mt-2 flex flex-wrap items-baseline gap-x-3">
          <b className={cn("font-num leading-[.85]", strong ? "text-[5.5rem] md:text-[8.5rem]" : "text-[5.5rem] opacity-80 md:text-[8.5rem]")}>
            {c.n}
          </b>
          <span className="font-num text-[1.5rem] md:text-[2.25rem]">{fmt(t.afterOf, { of: c.of })}</span>
        </span>
        <span className="mt-2 block text-[1.0625rem] font-semibold md:text-[1.25rem]">{zone}</span>
      </figcaption>
      <div className="border-2 border-ink bg-paper p-2 shadow-[6px_6px_0_var(--ink)]">
        <Court court={c} label={fmt(t.afterLabel, { when, n: c.n, of: c.of })} />
      </div>
    </figure>
  );
  return (
    <div className="grid grid-cols-2 gap-x-5 gap-y-10 md:gap-x-10 lg:gap-x-16">
      {side(before, t.afterBefore, false)}
      {side(after, t.afterLater, true)}
    </div>
  );
}

/**
 * The pieces of the start page's week (lib/story.ts): the time stamp over each part, the evening
 * after the defeat, the message in the team chat, and the right wing before and after.
 */
import type { ReactNode } from "react";
import { HalfCourtLines } from "@/components/anlauf/court";
import { HALF_BOX } from "@/components/anlauf/geometry";
import { cn } from "@/lib/cn";
import { fmt } from "@/lib/i18n";
import type { StoryCourt } from "@/lib/story";
import type { Messages } from "@/messages/de";

/** «Samstag, 19 Uhr»: the time stamp over a part of the week, after a short band in the club colour. */
export function When({ children, dark = false }: { children: ReactNode; dark?: boolean }) {
  return (
    <p className={cn("flex items-center gap-3 font-mono text-base font-semibold tracking-wide uppercase md:text-[1.0625rem]", dark ? "text-[#dcdfe2]" : "text-ink")}>
      <i aria-hidden className="mark-band inline-block h-2 w-10 shrink-0" />
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
          {/* a player bar that never moved: the playhead at 0:00 of 60:00 */}
          <div className="mt-3 flex items-center gap-3 font-mono text-base text-[#dcdfe2]">
            <svg viewBox="0 0 20 20" className="size-6 shrink-0">
              <path d="M5 3l12 7-12 7z" fill="currentColor" />
            </svg>
            <span>0:00</span>
            <span className="relative h-1.5 flex-1 bg-[#3a3d42]">
              <i className="absolute -top-[5px] left-0 size-4 bg-ground" style={{ borderRadius: "50%" }} />
            </span>
            <span>60:00</span>
          </div>
          <p className="mt-2 text-[1.0625rem] text-[#dcdfe2]">{t.video}</p>
        </div>
      </div>
    </div>
  );
}

/** Tuesday: the link as it arrives in the team chat, and a player who saw it himself (W26, W28). */
export function TeamChat({ t, team }: { t: Messages["home"]["chat"]; team: string }) {
  return (
    <div role="img" aria-label={t.label} className="mx-auto w-full max-w-[24rem] border-2 border-ink bg-paper shadow-[6px_6px_0_var(--ink)]">
      <div aria-hidden>
        <div className="flex items-center gap-3 bg-ink px-4 py-3 text-ground">
          <span className="grid size-10 shrink-0 place-items-center bg-club font-bold text-club-ink">H1</span>
          <span className="min-w-0">
            <b className="block leading-tight">{t.group}</b>
            <span className="block text-base text-[#b9bec4]">{t.members}</span>
          </span>
        </div>
        <div className="flex flex-col gap-4 bg-[#e4e1da] px-3 py-5 sm:px-4">
          <div className="ml-auto w-[88%] border-2 border-ink bg-paper">
            <div className="m-1.5 bg-club px-3 pt-3 pb-6 [clip-path:polygon(0_0,100%_0,100%_78%,0_100%)]">
              <p className="font-slant text-[1.375rem] leading-[1.05] text-club-ink">{t.card}</p>
            </div>
            <div className="px-3 pt-1 pb-2">
              <p className="text-base font-semibold">{fmt(t.cardMeta, { team })}</p>
              <p className="font-mono text-[0.9375rem] text-ink-2">app.handball-intelligence.com</p>
            </div>
            <p className="border-t border-rule px-3 py-2 text-[1.0625rem] leading-snug">{t.message}</p>
            <p className="px-3 pb-2 text-right text-[0.9375rem] text-ink-2">
              {t.you} · {t.time}
            </p>
          </div>
          <div className="w-[80%] border-2 border-ink bg-ground px-3 py-2">
            <p className="text-[0.9375rem] font-bold text-club-text">{t.replyFrom}</p>
            <p className="text-[1.0625rem] leading-snug">{t.reply}</p>
            <p className="text-right text-[0.9375rem] text-ink-2">{t.replyTime}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

/** One half court with the goals conceded as dots: the right wing in ink, the rest faint. */
function Court({ court, label }: { court: StoryCourt; label: string }) {
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

/** Three matches later: the right wing before and after, as the season would show it (W27). */
export function BeforeAfter({ t, before, after, zone }: { t: Messages["home"]; before: StoryCourt; after: StoryCourt; zone: string }) {
  const side = (c: StoryCourt, when: string, strong: boolean) => (
    <figure className="m-0 min-w-0">
      <figcaption className="flex flex-wrap items-baseline gap-x-3">
        <span className="w-full text-base font-semibold text-ink-2">{when}</span>
        <b className={cn("font-num text-[4rem] leading-[.9] md:text-[5rem]", strong ? "text-club-text" : "text-ink")}>{c.n}</b>
        <span className="font-num text-[1.5rem] text-ink-2">{fmt(t.afterOf, { of: c.of })}</span>
        <span className="w-full text-[1.0625rem] font-semibold">{zone}</span>
      </figcaption>
      <div className="mt-4 border-2 border-ink bg-paper p-2">
        <Court court={c} label={fmt(t.afterLabel, { when, n: c.n, of: c.of })} />
      </div>
    </figure>
  );
  return (
    <div className="grid grid-cols-2 gap-4 sm:gap-8">
      {side(before, t.afterBefore, false)}
      {side(after, t.afterLater, true)}
    </div>
  );
}

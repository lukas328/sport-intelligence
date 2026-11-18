import type { ReactNode } from "react";

/*
 * The pictures on the right of a page head (components/wurf-head.tsx PageHead, BEFUNDE-3 U9):
 * each says at a glance what the page holds, in the site's boxes (ink frame, hard shadow, the
 * club colour for numerals and the one strong block). Plain markup, no script.
 */

const BOX = "border-2 border-ink shadow-[6px_6px_0_var(--ink)]";

/** «So funktioniert es»: the four steps as a short numbered sequence, each a jump to its step. */
export function StepsArt({ steps, label }: { steps: readonly { title: string }[]; label: string }) {
  return (
    <ol aria-label={label} className={`${BOX} grid grid-cols-2 gap-0.5 bg-ink lg:grid-cols-1`}>
      {steps.map((s, i) => (
        <li key={s.title} className="flex bg-paper">
          <a href={`#schritt-${i + 1}`} className="group flex min-h-16 w-full items-center gap-4 px-4 py-3 outline-offset-[-5px] lg:min-h-[4.25rem]">
            <span aria-hidden className="font-num w-8 shrink-0 text-[2.5rem] leading-[.8] text-club-text">
              {i + 1}
            </span>
            <span className="text-[1.0625rem] leading-tight font-bold group-hover:underline md:text-[1.1875rem]">{s.title}</span>
          </a>
        </li>
      ))}
    </ol>
  );
}

/** «Ratgeber»: the topics as tiles with the number of pages, each a jump to its list. */
export function TopicTiles({ tiles, label }: { tiles: { id: string; name: string; countText: string }[]; label: string }) {
  return (
    <ul aria-label={label} className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-2">
      {tiles.map((t) => (
        <li key={t.id} className="flex">
          <a href={`#${t.id}`} className="group flex w-full flex-col gap-2 border-2 border-ink bg-paper p-3 hover:bg-ink/5">
            <i aria-hidden className="mark-band ml-1 h-2 w-7" />
            <span className="text-[1.0625rem] leading-tight font-bold group-hover:underline md:text-[1.1875rem]">{t.name}</span>
            <span className="mt-auto text-base text-ink-2">{t.countText}</span>
          </a>
        </li>
      ))}
    </ul>
  );
}

/** «Preise»: the free start as the one strong block, the days large. */
export function TrialArt({ days, label }: { days: number; label: string }) {
  return (
    <p className={`${BOX} on-club flex items-end gap-4 bg-club p-5 text-club-ink md:p-7 lg:flex-col lg:items-start lg:gap-3`}>
      <b className="font-num text-[5.5rem] leading-[.78] md:text-[8rem] lg:text-[9rem]">{days}</b>
      <span className="font-slant pb-1 text-[1.5rem] leading-[1.05] md:text-[2rem]">{label}</span>
    </p>
  );
}

/** «Über uns»: the sentence the page is built on, set large in the club colour. */
export function PullLine({ children }: { children: ReactNode }) {
  return (
    <p className={`${BOX} on-club bg-club p-6 text-club-ink md:p-8`}>
      <span className="font-slant block text-[2.25rem] leading-[1.02] md:text-[2.875rem]">{children}</span>
    </p>
  );
}

/**
 * «Daten und Einwilligung»: how the consent link asks, point by point, each with its own yes or no.
 * An example, not a form: the answers are shown, not chosen.
 */
export function ConsentArt({ title, note, items, yes, no }: { title: string; note: string; items: readonly string[]; yes: string; no: string }) {
  // the example answers: yes to the team and the club, no to public highlights and to the training
  const answers = [true, true, false, false];
  return (
    <figure className="m-0">
      <div className={`${BOX} bg-paper`}>
        <p className="border-b-2 border-ink px-4 py-2.5 font-bold">{title}</p>
        <ul>
          {items.map((x, i) => (
            <li key={x} className="flex items-center justify-between gap-3 border-b border-rule px-4 py-2.5 last:border-b-0">
              <span className="min-w-0 text-[1.0625rem] leading-tight">
                {x}
                <span className="sr-only">: {answers[i] ? yes : no}</span>
              </span>
              <span aria-hidden className="flex shrink-0 border-2 border-ink text-base font-semibold">
                <span className={`px-2.5 py-1 ${answers[i] ? "bg-ink text-ground" : ""}`}>{yes}</span>
                <span className={`border-l-2 border-ink px-2.5 py-1 ${answers[i] ? "" : "bg-ink text-ground"}`}>{no}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>
      <figcaption className="mt-3 text-base text-ink-2">{note}</figcaption>
    </figure>
  );
}

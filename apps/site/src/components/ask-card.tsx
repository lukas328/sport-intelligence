import { DemoLink } from "@/components/kit";
import { fmt } from "@/lib/i18n";
import type { StoryAnswer } from "@/lib/story";
import type { Messages } from "@/messages/de";

/**
 * «Frag deine Spiele» (BEFUNDE-3 U6): one question to the app's assistant and its answer, as the
 * app shows it (apps/web assistant-view, apps/api services/assistant.py): the question in the
 * coach's words, a short answer, the source and the sample under it, the scenes as evidence and,
 * folded, the queries the figures come from. Every figure is the demo match's (lib/story.ts), so
 * nothing here is typed in by hand.
 */
export function AskCard({
  t,
  a,
  team,
  opp,
  scenesHref,
}: {
  t: Messages["home"]["ask"];
  a: StoryAnswer;
  team: string;
  opp: string;
  scenesHref: string;
}) {
  const [x, y] = a.shooters;
  const v = {
    n: a.n,
    of: a.of,
    first: a.first,
    second: a.second,
    a: x?.number ?? "",
    an: x?.n ?? "",
    b: y?.number ?? "",
    bn: y?.n ?? "",
    opp,
  };
  return (
    <div className="border-2 border-ink bg-paper text-ink shadow-[8px_8px_0_var(--ink)]">
      <p className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 bg-ink px-4 py-2.5 font-mono text-[0.9375rem] font-semibold text-ground md:px-5">
        <span className="uppercase">{t.bar}</span>
        <span>{team}</span>
      </p>
      <div className="grid gap-5 p-4 md:p-6">
        <p className="ml-auto max-w-[85%] bg-club px-4 py-3 text-[1.125rem] leading-snug font-semibold text-club-ink shadow-[inset_0_0_0_2px_var(--club-edge)]">
          {t.question}
        </p>
        <div>
          <p className="text-[1.125rem] leading-normal md:text-[1.1875rem]">{fmt(t.answer, v)}</p>
          <p className="mt-3 border-t border-rule pt-3 text-base text-ink-2">{fmt(t.source, v)}</p>
        </div>
        <DemoLink href={scenesHref} className="btn btn-ink gap-2.5 justify-self-start">
          <svg viewBox="0 0 20 20" aria-hidden className="size-4 shrink-0">
            <path d="M5 3l12 7-12 7z" fill="currentColor" />
          </svg>
          {fmt(t.scenes, { n: a.n })}
        </DemoLink>
        <details className="group border-t-2 border-ink pt-3">
          <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 font-semibold [&::-webkit-details-marker]:hidden">
            {fmt(t.how, { count: t.queries.length })}
            <svg viewBox="0 0 20 20" aria-hidden className="size-5 shrink-0 transition-transform group-open:rotate-180">
              <path d="M4 7l6 6 6-6" fill="none" stroke="currentColor" strokeWidth={2.4} />
            </svg>
          </summary>
          <ol className="mt-2 grid list-decimal gap-1.5 pl-6 font-mono text-[0.9375rem] text-ink-2">
            {t.queries.map((q) => (
              <li key={q}>{fmt(q, v)}</li>
            ))}
          </ol>
        </details>
      </div>
    </div>
  );
}

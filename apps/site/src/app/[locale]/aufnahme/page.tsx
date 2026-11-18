import type { Metadata } from "next";
import type { CSSProperties, ReactNode } from "react";
import Link from "next/link";
import { Faq } from "@/components/faq";
import { HallPlan } from "@/components/hall-plan";
import { JsonLd } from "@/components/json-ld";
import { KitScope } from "@/components/kit";
import { PrintButton } from "@/components/print-button";
import { ProductShot } from "@/components/product-shot";
import { Reveal } from "@/components/reveal";
import { PageHead, SectionHead } from "@/components/wurf-head";
import { fileVars } from "@/lib/files";
import { fmt, messages, type Locale } from "@/lib/i18n";
import { graph, howTo } from "@/lib/schema";
import { pageMeta } from "@/lib/seo";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMeta(locale, "aufnahme", messages(locale).seo.filming.title, messages(locale).seo.filming.description);
}

/** Fixed line breaks: each line of the text on its own line, so the notice breaks the same in print. */
function lines(text: string) {
  return text.split("\n").map((l) => (
    <span key={l} className="block">
      {l}
    </span>
  ));
}

/**
 * Filmen (K24): the short answer first, as a picture (the hall plan) and five rules, then the
 * matchday checklist, the upload in the app, the details folded away and the printable notice.
 * Everything longer lives in the guide «Handballspiel filmen» and the help «Spiel richtig filmen».
 * The rules are the steps of the HowTo, word for word.
 */
/** A sentence with links in it: each {name} becomes its link, the words around it stay text. */
function sentence(template: string, links: Record<string, [string, string]>) {
  return template.split(/(\{\w+\})/).map((part, i) => {
    const link = links[part.slice(1, -1)];
    return link ? (
      <Link key={i} href={link[0]} className="font-bold underline decoration-2 underline-offset-4 hover:decoration-[3px]">
        {link[1]}
      </Link>
    ) : (
      part
    );
  });
}

export default async function Filming({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.filming;
  const files = fileVars(m);
  return (
    <KitScope>
      <JsonLd
        data={graph(
          howTo(locale, "aufnahme", {
            name: t.head,
            description: t.lead,
            tools: [...t.tools],
            steps: t.rules.map((r) => ({ name: r.title, text: r.text })),
          }),
        )}
      />
      <Reveal />
      <div className="no-print">
        <PageHead kick={t.title} title={t.head} lead={t.lead} />
      </div>
      <div className="wrap">
        {/* 1 · the answer: where the camera goes, and five rules */}
        <section aria-labelledby="rules" className="no-print mt-10 grid grid-cols-1 items-start gap-10 md:mt-14 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] lg:gap-14">
          <div className="min-w-0 lg:sticky lg:top-6">
            <HallPlan label={t.planLabel} camera={t.planCamera} field={t.planField} corner={t.planCorner} />
          </div>
          <div className="min-w-0">
            <h2 id="rules" className="sr-only">
              {t.rulesTitle}
            </h2>
            <ol className="border-t-2 border-ink">
              {t.rules.map((r, i) => (
                <li
                  key={r.title}
                  id={`schritt-${i + 1}`}
                  data-reveal
                  style={{ "--d": i } as CSSProperties}
                  className="grid grid-cols-[3.5rem_minmax(0,1fr)] items-start gap-x-4 border-b border-rule py-5"
                >
                  <span aria-hidden className="grid size-14 place-items-center border-2 border-ink bg-paper">
                    {RULE_ICONS[i]}
                  </span>
                  <div>
                    <h3 className="flex items-baseline gap-3 text-[1.5rem] leading-tight md:text-[1.75rem]">
                      <span aria-hidden className="upright text-club-text">
                        {i + 1}
                      </span>
                      {r.title}
                    </h3>
                    <p className="mt-1">{r.text}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* 2 · the matchday checklist */}
        <section aria-labelledby="check" className="no-print mt-20 md:mt-28">
          <SectionHead
            id="check"
            title={t.checkTitle}
            note={
              <Link href={`/${locale}/vorlagen/spieltag/`} className="link">
                {t.checkPrint}
              </Link>
            }
          />
          <div className="mt-6 grid grid-cols-1 gap-8 md:grid-cols-3">
            {t.check.map((g, i) => (
              <div key={g.title} data-reveal style={{ "--d": i } as CSSProperties}>
                <h3 className="text-[1.375rem]">{g.title}</h3>
                <ul className="mt-2">
                  {g.items.map((x) => (
                    <li key={x} className="flex gap-3 border-b border-rule py-3">
                      <span aria-hidden className="mt-1 size-5 shrink-0 border-2 border-ink bg-paper" />
                      <span>{fmt(x, files)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        {/* 3 · then in the app */}
        <section aria-labelledby="after" className="no-print mt-20 grid grid-cols-1 items-center gap-8 md:mt-28 md:grid-cols-[minmax(0,1fr)_minmax(0,26rem)] md:gap-14">
          <div data-reveal>
            <h2 id="after" className="text-[2.25rem] md:text-[3rem]">
              {t.afterTitle}
            </h2>
            <p className="measure mt-3 text-[1.1875rem]">{t.afterText}</p>
            <Link href={`/${locale}/so-funktioniert-es/`} className="link mt-3">
              {m.cta.how}
            </Link>
          </div>
          <div data-reveal style={{ "--d": 1 } as CSSProperties}>
            <ProductShot name="step-upload" alt={t.afterAlt} labels={{}} sizes="(min-width: 768px) 26rem, calc(100vw - 2rem)" />
          </div>
        </section>

        {/* 4 · details, folded */}
        <section aria-labelledby="more" className="no-print mt-20 md:mt-28">
          <SectionHead id="more" title={t.moreTitle} />
          <div className="mt-2 max-w-[48rem]">
            <Faq items={t.more.map((f) => ({ q: f.q, a: <p>{fmt(f.a, files)}</p> }))} />
          </div>
          {/* the deeper pages in one sentence (U28) */}
          <p className="measure mt-6">
            {sentence(t.moreLine, {
              guide: [`/${locale}/ratgeber/handballspiel-filmen/`, t.guideLink],
              help: [`/${locale}/hilfe/aufnahme/`, t.helpLink],
              storage: [`/${locale}/rechner/speicher/`, t.storageLink],
            })}
          </p>
        </section>

        {/* 5 · the notice: readable from three metres, one A4 page, no hyphenation, a line to fill in by hand */}
        <section className="mt-20 grid grid-cols-1 items-start gap-8 md:mt-28 lg:grid-cols-[minmax(0,1fr)_minmax(0,38rem)] lg:gap-14 print:mt-0 print:block" aria-labelledby="notice">
          <div className="no-print">
            <h2 id="notice" className="text-[2.25rem] md:text-[3rem]">
              {t.noticeTitle}
            </h2>
            <p className="measure mt-3">{t.noticeLead}</p>
            <PrintButton label={t.print} />
          </div>
          <div className="notice-sheet flex flex-col border-4 border-ink bg-paper px-6 py-10 md:px-12 md:py-14">
            <p className="font-slant notice-text text-[2.25rem] leading-[1.1] [hyphens:none] [overflow-wrap:normal] md:text-[3rem]">{lines(t.notice)}</p>
            <p className="notice-sub mt-6 text-[1.375rem] leading-[1.25] font-bold [hyphens:none] [overflow-wrap:normal] md:text-[1.75rem]">{lines(t.noticeSub)}</p>
            <p className="notice-ask mt-10 flex items-end gap-3 text-[1.25rem] font-bold">
              <span className="shrink-0">{t.noticeAsk}</span>
              <span aria-hidden className="h-8 flex-1 border-b-2 border-ink" />
            </p>
          </div>
        </section>
      </div>
    </KitScope>
  );
}

/** Small drawings for the five rules, in the order of messages.filming.rules (decorative). */
const RULE_ICONS: ReactNode[] = [
  // phone or camera
  <svg key="device" viewBox="0 0 40 40" className="size-9" fill="none" stroke="var(--ink)" strokeWidth={2.5}>
    <rect x={4} y={9} width={11} height={21} />
    <path d="M8 26h3" />
    <rect x={19} y={14} width={17} height={12} />
    <circle cx={27.5} cy={20} r={3.2} stroke="var(--club-line)" />
  </svg>,
  // high up
  <svg key="high" viewBox="0 0 40 40" className="size-9" fill="none" stroke="var(--ink)" strokeWidth={2.5}>
    <rect x={7} y={5} width={12} height={8} fill="var(--club)" stroke="var(--club-line)" />
    <path d="M13 13v23M7 36h12" />
    <path d="M30 34V8M24.5 13.5 30 8l5.5 5.5" stroke="var(--club-line)" />
  </svg>,
  // both goals in the picture
  <svg key="goals" viewBox="0 0 40 40" className="size-9" fill="none" stroke="var(--ink)" strokeWidth={2.5}>
    <rect x={3} y={11} width={34} height={18} />
    <path d="M20 11v18" strokeWidth={1.5} />
    <path d="M3 15a5 5 0 0 1 0 10M37 15a5 5 0 0 0 0 10" stroke="var(--club-line)" />
  </svg>,
  // fixed on a tripod
  <svg key="fixed" viewBox="0 0 40 40" className="size-9" fill="none" stroke="var(--ink)" strokeWidth={2.5}>
    <rect x={12} y={5} width={16} height={10} fill="var(--club)" stroke="var(--club-line)" />
    <path d="M20 15v8M20 23 10 36M20 23v13M20 23l10 13" />
  </svg>,
  // panning is fine
  <svg key="pan" viewBox="0 0 40 40" className="size-9" fill="none" stroke="var(--ink)" strokeWidth={2.5}>
    <rect x={13} y={20} width={14} height={10} />
    <path d="M7 16Q20 4 33 16" stroke="var(--club-line)" />
    <path d="M7.5 9.5 7 16l6.4 .6M32.5 9.5 33 16l-6.4 .6" stroke="var(--club-line)" />
  </svg>,
];

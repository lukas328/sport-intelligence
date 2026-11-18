import type { Metadata } from "next";
import Link from "next/link";
import plans from "@handball/plans";
import { FindField, FindGroup, FindNone, Findable } from "@/components/help-find";
import { KitScope } from "@/components/kit";
import { JsonLd } from "@/components/json-ld";
import { PageHead, SectionHead } from "@/components/wurf-head";
import { faqPage, graph } from "@/lib/schema";
import { fileVars } from "@/lib/files";
import { fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { MailLine } from "@/components/mail-line";
import { HELP, type HelpEntry } from "../../../../content/help";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMeta(locale, "hilfe", messages(locale).seo.faq.title, messages(locale).seo.faq.description);
}

/** The themes of the questions, in this order (faq.items[].g). */
const THEMES = ["filmen", "analyse", "team", "preise"] as const;
/** The groups of the guides to the app. */
const GUIDE_GROUPS: HelpEntry["group"][] = ["start", "video", "team", "work", "account"];

/**
 * «Fragen» in the Ratgeber's frame (BEFUNDE-3 U7, U8): the questions by theme, each with its short
 * answer in view; what the product takes off the coach's hands opens under it. Then the guides to
 * the app, in the same column and type. One search in the head filters both (U9); a quiet column
 * on the right says where to go when nothing fits.
 */
export default async function Help({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.faq;
  const team = plans.plans.find((p) => p.plan === "team")!;
  const answer = (a: string) => fmt(a, { month: team.price_chf_month, year: team.price_chf_year, ...fileVars(m) });
  // a link after an answer, by the question's place in faq.items
  const links: Record<number, [string, string]> = {
    2: [`/${locale}/aufnahme/`, m.cta.filming],
    7: [`/${locale}/demo/`, m.cta.demo],
    9: [`/${locale}/preise/`, m.cta.pricing],
    10: [`/${locale}/daten/`, m.cta.data],
    11: [`/${locale}/daten/`, m.cta.data],
  };
  const questions = t.items.map((f, i) => ({ ...f, i, a: answer(f.a), text: `${f.q} ${answer(f.a)} ${f.hi}` }));
  const guides = HELP.filter((h) => h.listed !== false).map((e) => ({ ...e, text: `${e.title[locale]} ${e.summary[locale]} ${e.keywords[locale]}` }));
  const texts = [...questions.map((q) => q.text), ...guides.map((g) => g.text)];
  return (
    <KitScope>
      <JsonLd data={graph(faqPage(locale, "hilfe", questions.map((f) => ({ q: f.q, a: f.hi ? `${f.a} ${t.hiLabel} ${f.hi}` : f.a }))))} />
      <PageHead
        kick={t.title}
        title={t.head}
        lead={t.lead}
        aside={<FindField label={t.search} hint={t.searchHint} texts={texts} hits={t.hits} hitsOne={t.hitsOne} />}
      />
      <div className="wrap grid grid-cols-1 gap-x-14 lg:grid-cols-[minmax(0,1fr)_16rem] xl:grid-cols-[minmax(0,52rem)_minmax(0,1fr)]">
        <div className="min-w-0">
          {THEMES.map((g) => {
            const list = questions.filter((q) => q.g === g);
            return (
              <FindGroup key={g} texts={list.map((q) => q.text)} labelledBy={`q-${g}`} className="mt-14">
                <SectionHead id={`q-${g}`} title={t.groups[g]} />
                <ul>
                  {list.map((f) => (
                    <Findable key={f.q} text={f.text} className="border-b border-rule py-5">
                      <h3 className="text-[1.375rem] leading-tight font-bold md:text-[1.5rem]">{f.q}</h3>
                      <p className="measure mt-2">{f.a}</p>
                      {/* K12: first the answer, then what the product takes off the coach's hands */}
                      {f.hi && (
                        <details className="group measure mt-1">
                          <summary className="link list-none gap-2">
                            <svg viewBox="0 0 24 24" aria-hidden className="size-4 shrink-0">
                              <path d="M4 12h16" stroke="var(--ink)" strokeWidth={3} />
                              <path d="M12 4v16" stroke="var(--ink)" strokeWidth={3} className="group-open:hidden" />
                            </svg>
                            {t.more}
                            {/* the colon of «So hilft …:», so the summary and its answer read as one sentence */}
                            <span className="sr-only">{t.hiLabel.slice(t.more.length)}</span>
                          </summary>
                          <p className="mt-1 mb-2 border-l-4 border-club-text bg-paper px-4 py-3">{f.hi}</p>
                        </details>
                      )}
                      {links[f.i] && (
                        <Link href={links[f.i]![0]} className="link">
                          {links[f.i]![1]}
                        </Link>
                      )}
                    </Findable>
                  ))}
                </ul>
              </FindGroup>
            );
          })}

          <FindGroup texts={guides.map((g) => g.text)} labelledBy="guides" className="mt-20">
            <div id="anleitungen" className="scroll-mt-20">
              <SectionHead id="guides" title={t.guidesTitle} />
            </div>
            {GUIDE_GROUPS.map((group) => {
              const list = guides.filter((e) => e.group === group);
              if (!list.length) return null;
              return (
                <FindGroup key={group} texts={list.map((e) => e.text)} labelledBy={`h-${group}`} className="mt-8">
                  <h3 id={`h-${group}`} className="font-slant text-[1.375rem] md:text-[1.5rem]">
                    {m.help.groups[group]}
                  </h3>
                  <ul className="mt-2 border-t-2 border-ink">
                    {list.map((e) => (
                      <Findable key={e.slug} text={e.text} className="border-b border-rule">
                        <Link href={`/${locale}/hilfe/${e.slug}/`} className="group block py-4">
                          <span className="text-[1.375rem] leading-tight font-bold underline decoration-2 underline-offset-4 group-hover:decoration-[3px] md:text-[1.5rem]">
                            {e.title[locale]}
                          </span>
                          <span className="measure mt-1 block text-ink-2">{e.summary[locale]}</span>
                        </Link>
                      </Findable>
                    ))}
                  </ul>
                </FindGroup>
              );
            })}
          </FindGroup>

          <FindNone texts={texts} className="mt-14 border-t-2 border-ink pt-6">
            <p className="measure text-[1.1875rem] font-semibold">{t.noHits}</p>
          </FindNone>
        </div>

        {/* the quiet column: when nothing fits, write to us (U7) */}
        <aside aria-labelledby="not-found" className="mt-16 lg:mt-14">
          <div className="border-t-2 border-ink pt-5 lg:sticky lg:top-6">
            <h2 id="not-found" className="text-[1.75rem]">
              {t.asideTitle}
            </h2>
            <p className="mt-3 [overflow-wrap:anywhere]">
              <MailLine template={m.help.contact} />
            </p>
            <ul className="mt-3">
              <li>
                <a href="#anleitungen" className="link">
                  {t.asideGuides}
                </a>
              </li>
              <li>
                <Link href={`/${locale}/ratgeber/`} className="link">
                  {m.guides.metaTitle}
                </Link>
              </li>
            </ul>
          </div>
        </aside>
      </div>
    </KitScope>
  );
}

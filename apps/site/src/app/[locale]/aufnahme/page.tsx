import type { Metadata } from "next";
import Link from "next/link";
import { HallPlan } from "@/components/hall-plan";
import { KitScope } from "@/components/kit";
import { PrintButton } from "@/components/print-button";
import { PageHead, SectionHead } from "@/components/wurf-head";
import { fileVars } from "@/lib/files";
import { fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMeta(locale, "aufnahme", messages(locale).seo.filming.title, messages(locale).seo.filming.description);
}

/** The filming guide with a plan of the hall and the printable notice (addendum 01, 8). */
export default async function Filming({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.filming;
  const files = fileVars(m);
  return (
    <KitScope>
      <div className="no-print">
        <PageHead kick={t.title} title={t.head} lead={t.lead} />
      </div>
      <div className="wrap">
        <div className="no-print mt-12 grid grid-cols-1 gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,30rem)]">
          <div className="lg:order-2">
            <div className="lg:sticky lg:top-6">
              <HallPlan label={t.planLabel} camera={t.planCamera} field={t.planField} corner={t.planCorner} />
            </div>
          </div>
          <div>
            {t.sections.map((s) => (
              <section key={s.title} className="mb-10" aria-labelledby={`f-${s.title}`}>
                <h2 id={`f-${s.title}`} className="section-head text-[1.75rem] md:text-[2.125rem]">
                  {s.title}
                </h2>
                <ul className="measure">
                  {s.items.map((x) => (
                    <li key={x} className="flex gap-4 border-b border-rule py-4">
                      <i aria-hidden className="mark-band mt-[.45em] h-2.5 w-4 shrink-0" />
                      <span>{fmt(x, files)}</span>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
            <section aria-labelledby="more">
              <SectionHead id="more" title={t.moreTitle} as="h3" />
              <div className="flex flex-wrap gap-x-8">
                <Link href={`/${locale}/ratgeber/handballspiel-filmen/`} className="link">
                  {m.nav.guides}: {m.filming.guideLink}
                </Link>
                <Link href={`/${locale}/hilfe/aufnahme/`} className="link">
                  {m.nav.faq}: {m.filming.title}
                </Link>
              </div>
            </section>
          </div>
        </div>

        <section className="mt-16 print:mt-0" aria-labelledby="notice">
          <div className="no-print">
            <SectionHead id="notice" title={t.noticeTitle} />
            <p className="measure mt-3">{t.noticeLead}</p>
          </div>
          {/* the notice: readable from three metres, one A4 page, no hyphenation, a line to fill in by hand */}
          <div className="notice-sheet mt-6 flex flex-col border-4 border-ink bg-paper px-6 py-12 md:px-16 md:py-20">
            <p className="font-slant notice-text text-[2.25rem] leading-[1.1] [hyphens:none] [overflow-wrap:normal] [text-wrap:balance] md:text-[3.5rem]">{t.notice}</p>
            <p className="notice-ask mt-12 flex items-end gap-3 text-[1.25rem] font-bold">
              <span className="shrink-0">{t.noticeAsk}</span>
              <span aria-hidden className="h-8 flex-1 border-b-2 border-ink" />
            </p>
          </div>
          <PrintButton label={t.print} />
        </section>
      </div>
    </KitScope>
  );
}

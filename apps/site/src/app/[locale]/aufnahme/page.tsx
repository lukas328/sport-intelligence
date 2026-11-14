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
                <Link href={`/${locale}/blog/spiele-filmen-mit-dem-handy/`} className="link">
                  {m.nav.blog}
                </Link>
              </div>
            </section>
          </div>
        </div>

        <section className="mt-16" aria-labelledby="notice">
          <div className="no-print">
            <SectionHead id="notice" title={t.noticeTitle} />
            <p className="measure mt-3">{t.noticeLead}</p>
          </div>
          <div className="mt-6 border-4 border-ink bg-paper px-6 py-12 text-center md:px-16 md:py-20">
            <img src="/brand/wortmarke-quer-einfarbig.svg" alt="Handball Intelligence" width={2150} height={512} className="mx-auto h-10 w-auto" />
            <p className="font-slant mx-auto mt-8 max-w-[36rem] text-[2rem] leading-tight hyphens-auto md:text-[2.75rem]">{t.notice}</p>
          </div>
          <PrintButton label={t.print} />
        </section>
      </div>
    </KitScope>
  );
}

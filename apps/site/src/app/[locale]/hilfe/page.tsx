import type { Metadata } from "next";
import Link from "next/link";
import plans from "@handball/plans";
import { Faq } from "@/components/faq";
import { HelpSearch } from "@/components/help-search";
import { KitScope } from "@/components/kit";
import { JsonLd } from "@/components/json-ld";
import { PageHead, SectionHead, Updated } from "@/components/wurf-head";
import { faqPage, graph } from "@/lib/schema";
import { fileVars } from "@/lib/files";
import { fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { MailLine } from "@/components/mail-line";
import { HELP } from "../../../../content/help";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMeta(locale, "hilfe", messages(locale).seo.faq.title, messages(locale).seo.faq.description);
}

/** Questions for the coach first, then the guides to the app (listed ones only) with search. */
export default async function Help({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.faq;
  const team = plans.plans.find((p) => p.plan === "team")!;
  const answer = (a: string) => fmt(a, { month: team.price_chf_month, year: team.price_chf_year, ...fileVars(m) });
  const links: Record<number, [string, string]> = {
    2: [`/${locale}/aufnahme/`, m.cta.filming],
    7: [`/${locale}/demo/`, m.cta.demo],
    9: [`/${locale}/preise/`, m.cta.pricing],
    10: [`/${locale}/daten/`, m.cta.data],
    11: [`/${locale}/daten/`, m.cta.data],
  };
  return (
    <KitScope>
      <JsonLd data={graph(faqPage(locale, "hilfe", t.items.map((f) => ({ q: f.q, a: f.hi ? `${answer(f.a)} ${t.hiLabel} ${f.hi}` : answer(f.a) }))))} />
      <PageHead kick={t.title} title={t.head} lead={t.lead}>
        <Updated locale={locale} />
      </PageHead>
      <div className="wrap">
        <div className="mt-12 max-w-[52rem]">
          <Faq
            items={t.items.map((f, i) => ({
              q: f.q,
              a: (
                <>
                  <p>{answer(f.a)}</p>
                  {/* K12: first the answer, then what the product takes off the coach's hands */}
                  {f.hi && (
                    <p className="mt-3 border-l-4 border-club-text bg-paper px-4 py-3">
                      <b>{t.hiLabel}</b> {f.hi}
                    </p>
                  )}
                  {links[i] && (
                    <Link href={links[i][0]} className="link">
                      {links[i][1]}
                    </Link>
                  )}
                </>
              ),
            }))}
          />
        </div>
        <section aria-labelledby="guides" className="mt-20">
          <SectionHead id="guides" title={t.guidesTitle} />
          <HelpSearch entries={HELP.filter((h) => h.listed !== false)} locale={locale} t={m.help} />
        </section>
        <p className="mt-16 border-t-2 border-ink pt-6">
          <b>{m.help.more}</b> <MailLine template={m.help.contact} />
        </p>
      </div>
    </KitScope>
  );
}

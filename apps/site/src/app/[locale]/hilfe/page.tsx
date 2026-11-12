import type { Metadata } from "next";
import Link from "next/link";
import plans from "@handball/plans";
import { Faq } from "@/components/faq";
import { HelpSearch } from "@/components/help-search";
import { KitScope } from "@/components/kit";
import { PageHead, SectionHead } from "@/components/wurf-head";
import { fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { MailLine } from "@/components/mail-line";
import { HELP } from "../../../../content/help";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).faq;
  return pageMeta(locale, "hilfe", t.title, t.lead);
}

/** Questions for the coach first, then the guides to the app (listed ones only) with search. */
export default async function Help({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.faq;
  const team = plans.plans.find((p) => p.plan === "team")!;
  const links: Record<number, [string, string]> = {
    1: [`/${locale}/aufnahme/`, m.cta.filming],
    6: [`/${locale}/daten/`, m.cta.data],
    7: [`/${locale}/daten/`, m.cta.data],
    5: [`/${locale}/preise/`, m.cta.pricing],
  };
  return (
    <KitScope>
      <PageHead kick={t.title} title={t.head} lead={t.lead} />
      <div className="wrap">
        <div className="mt-12 max-w-[52rem]">
          <Faq
            items={t.items.map((f, i) => ({
              q: f.q,
              a: (
                <>
                  <p>{fmt(f.a, { month: team.price_chf_month, year: team.price_chf_year })}</p>
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

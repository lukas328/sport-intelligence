import type { Metadata } from "next";
import plans from "@handball/plans";
import { Faq } from "@/components/faq";
import { KitScope } from "@/components/kit";
import { PageHead, SectionHead } from "@/components/wurf-head";
import { APP_LOCALE, fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { registerUrl } from "@/lib/site";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).pricing;
  return pageMeta(locale, "preise", t.title, `${t.head} ${t.draft}`);
}

/**
 * Prices and limits from packages/plans/plans.json (generated from the API's plan table). Still
 * placeholders (OPEN_QUESTIONS Q-PROD-4), so the page says they are not final. Only the features
 * of the core are named, in the app's words; the goalkeeper add-on is left out (not in the core).
 */
export default async function Pricing({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.pricing;
  const names = t.featureNames as Record<string, string>;
  const team = plans.plans.find((p) => p.plan === "team")!;
  return (
    <KitScope>
      <PageHead kick={t.title} title={t.head} figure={team.price_chf_month} figureLabel={t.figureLabel}>
        <p className="mt-6 inline-block bg-attn px-3 py-1.5 text-[1.0625rem] font-semibold text-ink">{t.draft}</p>
      </PageHead>
      <div className="wrap">
        <div className="mt-12 border-t-2 border-ink">
          {plans.plans.map((p) => {
            const info = t.plans[p.plan as keyof typeof t.plans];
            const items = [
              fmt(p.teams > 1 ? t.teamsN : t.teams, { count: p.teams }),
              p.matches_per_season ? fmt(t.matchesN, { count: p.matches_per_season }) : t.matchesUnlimited,
              p.analysis ? t.withAnalysis : t.withoutAnalysis,
              ...p.features.filter((f) => f in names).map((f) => names[f]!),
              fmt(t.storage, { gb: p.storage_gb }),
            ];
            return (
              <section key={p.plan} aria-labelledby={`plan-${p.plan}`} className="grid grid-cols-1 gap-x-10 gap-y-4 border-b border-rule py-10 md:grid-cols-[minmax(0,16rem)_minmax(0,1fr)_auto]">
                <div>
                  <h2 id={`plan-${p.plan}`} className="text-[2.25rem]">
                    {info.name}
                  </h2>
                  <p className="mt-2 text-[1.0625rem] text-ink-2">{info.text}</p>
                </div>
                <ul>
                  {items.map((x) => (
                    <li key={x} className="flex gap-3 py-1.5">
                      <i aria-hidden className="mark-band mt-[.5em] h-2 w-3.5 shrink-0" />
                      <span>{x}</span>
                    </li>
                  ))}
                </ul>
                <div className="md:text-right">
                  {p.price_chf_month ? (
                    <>
                      <p className="font-num text-[3.5rem] leading-none">{p.price_chf_month}</p>
                      <p className="font-semibold">{fmt(t.perMonth, { price: p.price_chf_month })}</p>
                      <p className="text-[1.0625rem] text-ink-2">{fmt(t.perYear, { price: p.price_chf_year })}</p>
                    </>
                  ) : (
                    <p className="font-num text-[3.5rem] leading-none">{t.free}</p>
                  )}
                  <a href={registerUrl(APP_LOCALE[locale])} className={`btn mt-5 w-full md:w-auto ${p.plan === "team" ? "btn-ink" : "btn-line"}`}>
                    {t.choose}
                  </a>
                  {p.trial_days > 0 && <p className="mt-2 text-[1.0625rem] text-ink-2">{fmt(t.trial, { days: p.trial_days })}</p>}
                </div>
              </section>
            );
          })}
        </div>
        <div className="mt-6 space-y-1 text-[1.0625rem] text-ink-2">
          <p>{fmt(t.annual, { months: plans.annual_months })}</p>
          <p>{t.currency}</p>
        </div>
        <section aria-labelledby="faq" className="mt-16">
          <SectionHead id="faq" title={t.faqTitle} />
          <Faq items={t.faq.map((f) => ({ q: f.q, a: <p>{f.a}</p> }))} />
        </section>
      </div>
    </KitScope>
  );
}

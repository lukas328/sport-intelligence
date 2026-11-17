import type { Metadata } from "next";
import plans from "@handball/plans";
import { Faq } from "@/components/faq";
import { KitScope, StartLink } from "@/components/kit";
import { JsonLd } from "@/components/json-ld";
import { TrialArt } from "@/components/head-art";
import { PageHead, SectionHead } from "@/components/wurf-head";
import { faqPage, graph } from "@/lib/schema";
import { APP_LOCALE, fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMeta(
    locale,
    "preise",
    messages(locale).seo.pricing.title,
    messages(locale).seo.pricing.description,
  );
}

/**
 * Prices and limits from packages/plans/plans.json (generated from the API's plan table). The free
 * start comes first (BEFUNDE-2 L10): 30 days with everything, then Team or the free plan; the plans
 * follow. Only the features of the core are named, in the app's words; the goalkeeper add-on is
 * left out (not in the core).
 */
export default async function Pricing({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.pricing;
  const names = t.featureNames as Record<string, string>;
  const team = plans.plans.find((p) => p.plan === "team")!;
  const nums = { days: team.trial_days, month: team.price_chf_month, year: team.price_chf_year };
  return (
    <KitScope>
      <JsonLd
        data={graph(
          faqPage(
            locale,
            "preise",
            t.faq.map((f) => ({ q: f.q, a: f.a })),
          ),
        )}
      />
      <PageHead
        kick={t.title}
        title={t.head}
        lead={fmt(t.lead, nums)}
        aside={<TrialArt days={team.trial_days} label={t.figureLabel} />}
      >
        <StartLink appLocale={APP_LOCALE[locale]} className="btn btn-ink mt-8">
          {t.choose}
        </StartLink>
      </PageHead>
      <div className="wrap">
        {/* the way it goes: today free with everything, after the trial Team or the free plan */}
        <ol
          aria-label={t.pathLabel}
          className="mt-10 grid grid-cols-1 md:mt-14 md:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]"
        >
          {t.path.map((s, i) => (
            <li
              key={s.title}
              className={
                i === 0
                  ? "on-club relative border-2 border-ink bg-club p-6 text-club-ink shadow-[6px_6px_0_var(--ink)] md:p-8"
                  : "relative border-2 border-ink bg-paper p-6 max-md:mt-6 max-md:ml-6 md:-ml-0.5 md:mt-8 md:p-8"
              }
            >
              <p className="flex items-center gap-3 font-mono text-base font-semibold tracking-wide uppercase">
                <span
                  aria-hidden
                  className={
                    i === 0
                      ? "font-num text-[2rem] leading-none normal-case"
                      : "font-num text-[2rem] leading-none text-club-text normal-case"
                  }
                >
                  {i + 1}
                </span>
                {fmt(s.when, nums)}
              </p>
              <h2 className="mt-3 text-[1.875rem] leading-tight md:text-[2.375rem]">
                {fmt(s.title, nums)}
              </h2>
              <p className="mt-3 max-w-[30rem] text-[1.125rem]">{fmt(s.text, nums)}</p>
            </li>
          ))}
        </ol>
        <h2 className="mt-16 text-[1.875rem] md:mt-20 md:text-[2.375rem]">{t.plansTitle}</h2>
        <div className="mt-4 border-t-2 border-ink">
          {plans.plans.map((p) => {
            const info = t.plans[p.plan as keyof typeof t.plans];
            const items = [
              fmt(p.teams > 1 ? t.teamsN : t.teams, { count: p.teams }),
              p.matches_per_season
                ? fmt(t.matchesN, { count: p.matches_per_season })
                : t.matchesUnlimited,
              p.analysis ? t.withAnalysis : t.withoutAnalysis,
              ...p.features.filter((f) => f in names).map((f) => names[f]!),
              fmt(t.storage, { gb: p.storage_gb }),
            ];
            return (
              <section
                key={p.plan}
                aria-labelledby={`plan-${p.plan}`}
                className="grid grid-cols-1 gap-x-10 gap-y-4 border-b border-rule py-10 md:grid-cols-[minmax(0,16rem)_minmax(0,1fr)_auto]"
              >
                <div>
                  <h3 id={`plan-${p.plan}`} className="font-slant text-[2.25rem] leading-tight">
                    {info.name}
                  </h3>
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
                      <p className="font-semibold">
                        {fmt(t.perMonth, { price: p.price_chf_month })}
                      </p>
                      <p className="text-[1.0625rem] text-ink-2">
                        {fmt(t.perYear, { price: p.price_chf_year })}
                      </p>
                    </>
                  ) : (
                    <p className="font-num text-[3.5rem] leading-none">{t.free}</p>
                  )}
                  <StartLink
                    appLocale={APP_LOCALE[locale]}
                    className={`btn mt-5 w-full md:w-auto ${p.plan === "team" ? "btn-ink" : "btn-line"}`}
                  >
                    {t.choose}
                  </StartLink>
                  {p.trial_days > 0 && (
                    <p className="mt-2 text-[1.0625rem] text-ink-2">
                      {fmt(t.trial, { days: p.trial_days })}
                    </p>
                  )}
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

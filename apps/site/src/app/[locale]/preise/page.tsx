import type { Metadata } from "next";
import plans from "@handball/plans";
import { APP_LOCALE, fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { registerUrl } from "@/lib/site";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).pricing;
  return pageMeta(locale, "preise", t.title, t.lead);
}

/** Prices and limits come from packages/plans/plans.json, generated from the API's plan table. */
export default async function Pricing({ params }: Props) {
  const { locale } = await params;
  const t = messages(locale).pricing;
  const names = t.featureNames as Record<string, string>;
  return (
    <>
      <h1 className="text-3xl font-bold">{t.title}</h1>
      <p className="mt-3 max-w-2xl text-lg text-muted">{t.lead}</p>
      <div className="mt-8 grid gap-5 md:grid-cols-3">
        {plans.plans.map((p) => {
          const info = t.plans[p.plan as keyof typeof t.plans];
          return (
            <section key={p.plan} className="flex flex-col rounded-2xl bg-raised ring-1 ring-border/70 p-6" aria-labelledby={`plan-${p.plan}`}>
              <h2 id={`plan-${p.plan}`} className="text-xl font-bold">{info.name}</h2>
              <p className="mt-1 text-sm text-muted">{info.text}</p>
              <p className="mt-4 text-3xl font-bold">
                {p.price_chf_month ? `CHF ${p.price_chf_month}` : t.free}
                {p.price_chf_month ? <span className="text-base font-normal text-muted"> {t.perMonth}</span> : null}
              </p>
              {p.price_chf_year ? <p className="text-sm text-muted">{fmt(t.perYear, { price: p.price_chf_year })}</p> : null}
              <ul className="mt-5 flex-1 space-y-1.5 text-sm">
                <li>{fmt(p.teams > 1 ? t.teamsN : t.teams, { count: p.teams })}</li>
                <li>{p.matches_per_season ? fmt(t.matchesN, { count: p.matches_per_season }) : t.matchesUnlimited}</li>
                <li>{fmt(t.storage, { gb: p.storage_gb })}</li>
                <li>{p.analysis ? t.withAnalysis : t.withoutAnalysis}</li>
                {p.features.map((f) => (
                  <li key={f}>{names[f] ?? f}</li>
                ))}
              </ul>
              <a
                href={registerUrl(APP_LOCALE[locale])}
                className="mt-6 rounded-full bg-accent px-5 py-2.5 text-center font-semibold text-accent-contrast"
              >
                {p.trial_days ? fmt(t.trial, { days: p.trial_days }) : fmt(t.choose, { plan: info.name })}
              </a>
            </section>
          );
        })}
      </div>
      <div className="mt-6 space-y-1 text-sm text-muted">
        <p>{fmt(t.goalkeeper, { price: plans.goalkeeper_addon_chf_month })}</p>
        <p>{fmt(t.annual, { months: plans.annual_months })}</p>
        <p>{t.currency}</p>
      </div>
      <section className="mt-12 max-w-3xl">
        <h2 className="text-2xl font-bold">{t.faqTitle}</h2>
        <dl className="mt-4 space-y-4">
          {t.faq.map((f) => (
            <div key={f.q}>
              <dt className="font-semibold">{f.q}</dt>
              <dd className="mt-1 text-muted">{f.a}</dd>
            </div>
          ))}
        </dl>
      </section>
    </>
  );
}

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
import { cn } from "@/lib/cn";

type Plan = (typeof plans.plans)[number];
/** the plan features named on the page, in this order (packages/plans/plans.json) */
const FEATURE_ROWS = ["insights", "assistant", "season", "tactics", "share_links", "pdf_reports", "club_stats", "priority"] as const;

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
 * start comes first (BEFUNDE-2 L10): 30 days with everything, then Team or the free plan; then the
 * plans side by side in one table with ticks (BEFUNDE-3 U23), in the app's words. The goalkeeper
 * figures are part of Team and Verein without extra charge (A9), not of the free plan (Lukas,
 * 18.11.2026), so no add-on price appears here.
 */
export default async function Pricing({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.pricing;
  const names = t.featureNames as Record<string, string>;
  const team = plans.plans.find((p) => p.plan === "team")!;
  const nums = { days: team.trial_days, month: team.price_chf_month, year: team.price_chf_year };
  const list = plans.plans;
  // the yearly price in months given: CHF 390 for 12 months of CHF 39 is «2 Monate geschenkt»
  const gift = (p: Plan) => Math.round(12 - p.price_chf_year / p.price_chf_month);
  const has = (f: string) => (p: Plan) => (p.features as string[]).includes(f);
  const subs = t.featureSubs as Record<string, string>;
  // the rows of the comparison: limits, then what is in, in the app's words and in this order
  const rows: { key: string; name: string; sub?: string; value: (p: Plan) => string | boolean }[] = [
    { key: "teams", name: t.rowTeams, value: (p) => fmt(p.teams > 1 ? t.teamsN : t.teams, { count: p.teams }) },
    {
      key: "matches",
      name: t.rowMatches,
      value: (p) => (p.matches_per_season ? fmt(t.matchesN, { count: p.matches_per_season }) : `${t.matchesAll}, ${t.fairUse}`),
    },
    { key: "storage", name: t.rowStorage, value: (p) => fmt(t.storage, { gb: p.storage_gb }) },
    { key: "events", name: names.events!, value: has("events") },
    { key: "analysis", name: t.analysis, sub: t.analysisSub, value: (p) => p.analysis },
    // the goalkeeper module: Team and Verein without an add-on (A9), not Gratis (Lukas, 18.11.2026)
    { key: "goalkeepers", name: t.goalkeepers, sub: t.goalkeepersSub, value: has("goalkeepers") },
    ...FEATURE_ROWS.map((f) => ({ key: f, name: names[f]!, sub: subs[f], value: has(f) })),
  ];
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
                      ? "upright text-[1.75rem] leading-none normal-case"
                      : "upright text-[1.75rem] leading-none text-club-text normal-case"
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
        <h2 id="plaene" className="mt-16 text-[1.875rem] md:mt-20 md:text-[2.375rem]">
          {t.plansTitle}
        </h2>
        {/* the plans side by side (U23): one column per plan, one row per thing, ticks where it is in */}
        <div className="mt-6 max-md:hidden">
          <table aria-describedby="fair" className="w-full border-collapse text-left">
            <caption className="sr-only">{t.compareLabel}</caption>
            <colgroup>
              <col className="w-[38%] md:w-[40%]" />
              {list.map((p) => (
                <col key={p.plan} className={p.plan === "team" ? "bg-paper" : undefined} />
              ))}
            </colgroup>
            <thead>
              <tr className="border-y-2 border-ink align-top">
                <td />
                {list.map((p) => {
                  const info = t.plans[p.plan as keyof typeof t.plans];
                  return (
                    <th key={p.plan} scope="col" className={cn("px-2 pt-5 pb-5 font-normal md:px-5", p.plan === "team" && "border-x-2 border-ink")}>
                      <span className="block font-slant text-[1.5rem] leading-tight md:text-[2rem]">{info.name}</span>
                      <span className="mt-1 block text-base text-ink-2 max-md:hidden">{info.text}</span>
                      {p.price_chf_month ? (
                        <span className="mt-4 block">
                          <span className="font-num block text-[2.25rem] leading-none md:text-[3rem]">{p.price_chf_month}</span>
                          <span className="mt-1 block text-[0.9375rem] font-semibold md:text-base">
                            {fmt(t.perMonth, { price: p.price_chf_month })}
                          </span>
                          <span className="block text-[0.9375rem] text-ink-2 md:text-base">
                            {fmt(t.perYear, { price: p.price_chf_year, gift: gift(p) })}
                          </span>
                        </span>
                      ) : (
                        <span className="mt-4 block">
                          <span className="font-num block text-[2.25rem] leading-none md:text-[3rem]">0</span>
                          <span className="mt-1 block text-[0.9375rem] font-semibold md:text-base">
                            {fmt(t.perMonth, { price: 0 })}
                          </span>
                        </span>
                      )}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.key} className="border-b border-rule align-top">
                  <th scope="row" className="py-3 pr-3 font-normal">
                    <span className="block font-semibold">{r.name}</span>
                    {r.sub && <span className="mt-0.5 block text-[0.9375rem] leading-snug text-ink-2">{r.sub}</span>}
                  </th>
                  {list.map((p) => {
                    const v = r.value(p);
                    return (
                      <td key={p.plan} className={cn("px-2 py-3 md:px-5", p.plan === "team" && "border-x-2 border-ink")}>
                        {v === true ? (
                          <>
                            <Tick />
                            <span className="sr-only">{t.yes}</span>
                          </>
                        ) : v === false ? (
                          <>
                            <span aria-hidden className="block pt-0.5 text-ink-2">
                              -
                            </span>
                            <span className="sr-only">{t.no}</span>
                          </>
                        ) : (
                          <span className="block font-semibold">{v}</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-b-2 border-ink align-top">
                <td />
                {list.map((p) => (
                  <td key={p.plan} className={cn("px-2 pt-5 pb-6 md:px-5", p.plan === "team" && "border-x-2 border-ink")}>
                    <StartLink
                      appLocale={APP_LOCALE[locale]}
                      className={cn("btn w-full px-3 max-md:text-[0.9375rem] md:w-auto", p.plan === "team" ? "btn-ink" : "btn-line")}
                    >
                      {t.choose}
                    </StartLink>
                    {p.trial_days > 0 && (
                      <p className="mt-2 text-[0.9375rem] text-ink-2 md:text-base">
                        {fmt(t.trial, { days: p.trial_days })}
                      </p>
                    )}
                  </td>
                ))}
              </tr>
            </tfoot>
          </table>
        </div>
        {/* on the phone: the same table, each row's name on its own line over the three plans */}
        <table aria-describedby="fair" className="mt-6 w-full table-fixed border-collapse text-left md:hidden">
          <caption className="sr-only">{t.compareLabel}</caption>
          <thead>
            <tr className="border-y-2 border-ink align-top">
              {list.map((p) => (
                <th key={p.plan} id={`m-${p.plan}`} scope="col" className="px-1.5 pt-4 pb-3 font-normal first:pl-0">
                  <span className="block font-slant text-[1.375rem] leading-tight">{t.plans[p.plan as keyof typeof t.plans].name}</span>
                  <span className="font-num mt-2 block text-[2rem] leading-none">{p.price_chf_month}</span>
                  <span className="mt-1 block text-[0.875rem] leading-snug font-semibold">{fmt(t.perMonth, { price: p.price_chf_month })}</span>
                </th>
              ))}
            </tr>
          </thead>
          {rows.map((r) => (
            <tbody key={r.key} className="border-b border-rule">
              <tr>
                <th id={`m-${r.key}`} colSpan={3} scope="colgroup" className="pt-3 pb-1 font-normal">
                  <span className="block font-semibold">{r.name}</span>
                  {r.sub && <span className="block text-[0.9375rem] leading-snug text-ink-2">{r.sub}</span>}
                </th>
              </tr>
              <tr className="align-top">
                {list.map((p) => {
                  const v = r.value(p);
                  return (
                    <td key={p.plan} headers={`m-${p.plan} m-${r.key}`} className="px-1.5 pb-3 first:pl-0">
                      {v === true ? (
                        <>
                          <Tick />
                          <span className="sr-only">{t.yes}</span>
                        </>
                      ) : v === false ? (
                        <>
                          <span aria-hidden className="block text-ink-2">
                            -
                          </span>
                          <span className="sr-only">{t.no}</span>
                        </>
                      ) : (
                        <span className="block text-[0.9375rem] font-semibold">{v}</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            </tbody>
          ))}
        </table>
        <div className="mt-5 flex flex-col gap-2 md:hidden">
          <StartLink appLocale={APP_LOCALE[locale]} className="btn btn-ink">
            {t.choose}
          </StartLink>
          <p className="text-[1.0625rem] text-ink-2">{fmt(t.trial, { days: team.trial_days })}</p>
        </div>
        <div className="mt-6 max-w-[48rem] space-y-2 text-[1.0625rem] text-ink-2">
          <p id="fair">{t.fairUseText}</p>
          <p>{fmt(t.annual, { months: plans.annual_months, gift: gift(team) })}</p>
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

function Tick() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden className="mt-0.5 size-5 text-club-text">
      <path d="M3 10.5 8 15 17 5" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="square" />
    </svg>
  );
}

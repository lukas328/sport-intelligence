import type { Metadata } from "next";
import Link from "next/link";
import plans from "@handball/plans";
import { Cur, CurrencySwitch } from "@/components/currency";
import { KitScope, StartLink } from "@/components/kit";
import { MailLine } from "@/components/mail-line";
import { PageHead, SectionHead } from "@/components/wurf-head";
import { cn } from "@/lib/cn";
import { perTeam } from "@/lib/currency";
import { APP_LOCALE, fmt, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).seo.clubs;
  return pageMeta(locale, "vereine", t.title, t.description);
}

/**
 * «Für Vereine» (BEFUNDE-5, row 24): for the board that pays the Club plan. Only product facts:
 * the plan's limits and features from packages/plans, the data and consent in one block as on
 * «Daten», and the contact. No voices, no logos.
 */
export default async function Clubs({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.clubs;
  const p = m.pricing;
  const team = plans.plans.find((x) => x.plan === "team")!;
  const club = plans.plans.find((x) => x.plan === "club")!;
  const names = p.featureNames as Record<string, string>;
  const both = [team, club];
  const has = (f: string) => (x: (typeof both)[number]) => (x.features as string[]).includes(f);
  const rows: { key: string; name: string; value: (x: (typeof both)[number]) => string | boolean }[] = [
    { key: "price", name: t.rowPrice, value: (x) => fmt(p.perMonth, { price: x.price_chf_month }) },
    { key: "teams", name: p.rowTeams, value: (x) => fmt(x.teams > 1 ? p.teamsN : p.teams, { count: x.teams }) },
    { key: "storage", name: p.rowStorage, value: (x) => fmt(p.storage, { gb: x.storage_gb }) },
    { key: "analysis", name: p.analysis, value: (x) => x.analysis },
    { key: "club_stats", name: names.club_stats!, value: has("club_stats") },
    { key: "priority", name: names.priority!, value: has("priority") },
  ];
  const vars = { teams: club.teams, price: club.price_chf_month, perTeam: perTeam(club), gb: club.storage_gb };
  return (
    <KitScope>
      <PageHead kick={t.title} title={t.head} lead={t.lead}>
        <StartLink appLocale={APP_LOCALE[locale]} src="clubs" className="btn btn-ink mt-8">
          {m.cta.start}
        </StartLink>
      </PageHead>
      <div className="wrap">
        <section aria-labelledby="get">
          <SectionHead id="get" title={t.getTitle} />
          <ul className="measure mt-6 border-t-2 border-ink">
            {t.get.map((x) => (
              <li key={x} className="flex gap-3 border-b border-rule py-3">
                <i aria-hidden className="mark-band mt-[.5em] h-2 w-3.5 shrink-0" />
                <span>
                  <Cur text={fmt(x, vars)} />
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="compare" className="mt-16">
          <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
            <SectionHead id="compare" title={t.compareTitle} />
            <CurrencySwitch label={p.currencyLabel} />
          </div>
          <table className="mt-6 w-full max-w-[44rem] table-fixed border-collapse text-left">
            <caption className="sr-only">{t.compareTitle}</caption>
            <thead>
              <tr className="border-y-2 border-ink align-top">
                <td className="w-[40%]" />
                {both.map((x) => (
                  <th key={x.plan} scope="col" className="px-2 py-4 font-normal">
                    <span className="block font-slant text-[1.375rem] leading-tight md:text-[1.75rem]">{p.plans[x.plan as "team" | "club"].name}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.key} className="border-b border-rule align-top">
                  <th scope="row" className="py-3 pr-2 font-semibold">
                    {r.name}
                  </th>
                  {both.map((x) => {
                    const v = r.value(x);
                    return (
                      <td key={x.plan} className={cn("px-2 py-3", typeof v === "string" && "font-semibold")}>
                        {v === true ? p.yes : v === false ? <span className="text-ink-2">-<span className="sr-only">{p.no}</span></span> : <Cur text={v} />}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-4 max-w-[44rem] text-[1.0625rem] text-ink-2">
            {p.currency} {fmt(p.annual, { months: plans.annual_months, gift: Math.round(12 - club.price_chf_year / club.price_chf_month) })}
          </p>
          <Link href={`/${locale}/preise/`} className="link mt-2">
            {m.cta.pricing}
          </Link>
        </section>

        <section aria-labelledby="data" className="mt-16">
          <SectionHead id="data" title={t.dataTitle} />
          <p className="measure mt-4">{t.data}</p>
          <p className="measure mt-3">{m.data.board}</p>
          <div className="flex flex-wrap gap-x-8">
            <Link href={`/${locale}/daten/`} className="link">
              {m.cta.data}
            </Link>
            <Link href={`/${locale}/datenschutz/`} className="link">
              {m.data.privacyLink}
            </Link>
          </div>
        </section>

        <section aria-labelledby="contact" className="mt-16">
          <SectionHead id="contact" title={t.contactTitle} />
          <p className="measure mt-4">
            <MailLine template={fmt(t.contact, { teams: club.teams })} />
          </p>
        </section>
      </div>
    </KitScope>
  );
}

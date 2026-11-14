import type { Metadata } from "next";
import Link from "next/link";
import { Honest } from "@/components/honest";
import { JsonLd } from "@/components/json-ld";
import { KitScope } from "@/components/kit";
import { PageHead, SectionHead } from "@/components/wurf-head";
import { factRows } from "@/lib/facts";
import { HTML_LANG, fmt, messages, type Locale } from "@/lib/i18n";
import { APP_ID, graph, organization, softwareApplication, webPage, website } from "@/lib/schema";
import { pageMeta } from "@/lib/seo";
import { LAUNCHED, SITE_UPDATED, pageUrl } from "@/lib/site";
import { launchState } from "@/lib/files";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).facts;
  return pageMeta(locale, "fakten", t.metaTitle, t.description);
}

/**
 * «Fakten auf einen Blick»: the same statements as the rest of the site, as text and as a table,
 * short enough to be quoted word for word (by people and by AI assistants). Same source as llms.txt.
 */
export default async function Facts({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.facts;
  const rows = factRows(locale);
  const date = new Intl.DateTimeFormat(HTML_LANG[locale], { dateStyle: "long", timeZone: "Europe/Zurich" }).format(new Date(SITE_UPDATED));
  const links: [string, string][] = [
    ["so-funktioniert-es", m.nav.how],
    ["aufnahme", m.nav.filming],
    ["preise", m.nav.pricing],
    ["daten", m.nav.data],
    ["ratgeber", m.nav.guides],
    ["ueber-uns", m.nav.us],
    ["hilfe", m.nav.faq],
  ];
  return (
    <KitScope>
      <JsonLd
        data={graph(
          organization(),
          website(locale),
          softwareApplication(locale, t.lead, m.pricing.plans),
          { ...webPage(locale, "fakten", t.metaTitle, t.description, SITE_UPDATED, "AboutPage"), about: { "@id": APP_ID } },
        )}
      />
      <PageHead kick={t.title} title={t.head} lead={t.lead}>
        <p className="mt-5 text-[1.0625rem] text-ink-2">
          <time dateTime={SITE_UPDATED}>{fmt(m.guides.updated, { date })}</time>
        </p>
        {!LAUNCHED && <p className="mt-4 max-w-[40rem] border-l-4 border-attn bg-paper px-4 py-2 text-[1.0625rem]">{launchState(m)}</p>}
      </PageHead>
      <div className="wrap">
        <section aria-labelledby="fakten" className="mt-12">
          <SectionHead id="fakten" title={t.tableTitle} />
          <table className="mt-2 block w-full max-w-[56rem] border-collapse md:table">
            <caption className="sr-only">{t.tableCaption}</caption>
            <tbody className="block md:table-row-group">
              {rows.map((r) => (
                <tr key={r.k} className="block border-b border-rule align-top md:table-row">
                  <th scope="row" className="block pt-4 text-left font-bold md:table-cell md:w-[14rem] md:py-4 md:pr-4">
                    {r.k}
                  </th>
                  <td className="block pb-4 leading-[1.55] [overflow-wrap:anywhere] md:table-cell md:pt-4">{r.v.includes("@") ? <a href={`mailto:${r.v}`} className="link">{r.v}</a> : r.v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section aria-labelledby="kann" className="mt-16">
          <SectionHead id="kann" title={t.canTitle} />
          <div className="mt-8">
            <Honest t={m.honest} />
          </div>
        </section>

        <section aria-labelledby="wer" className="mt-16">
          <SectionHead id="wer" title={m.us.homeTitle} />
          <p className="measure mt-4">{m.us.homeText}</p>
          <Link href={`/${locale}/ueber-uns/`} className="link mt-2">
            {m.us.homeLink}
          </Link>
        </section>

        <section aria-labelledby="zitieren" className="mt-16">
          <SectionHead id="zitieren" title={t.quoteTitle} />
          <p className="measure mt-3">
            {t.quote} <span className="break-all">{pageUrl(locale, "fakten")}</span>
          </p>
          <h3 className="font-slant mt-8 text-[1.5rem]">{t.more}</h3>
          <ul className="mt-2 flex flex-wrap gap-x-8">
            {links.map(([href, label]) => (
              <li key={href}>
                <Link href={`/${locale}/${href}/`} className="link">
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </KitScope>
  );
}

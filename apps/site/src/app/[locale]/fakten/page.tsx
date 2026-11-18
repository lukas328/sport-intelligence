import type { Metadata } from "next";
import Link from "next/link";
import { Honest } from "@/components/honest";
import { JsonLd } from "@/components/json-ld";
import { KitScope } from "@/components/kit";
import { PageHead, SectionHead, Updated } from "@/components/wurf-head";
import { factRows } from "@/lib/facts";
import { messages, type Locale } from "@/lib/i18n";
import type { Messages } from "@/messages/de";
import { GUIDES } from "../../../../content/ratgeber";
import { APP_ID, graph, organization, softwareApplication, webPage, website } from "@/lib/schema";
import { pageMeta } from "@/lib/seo";
import { PAGE_UPDATED, SITE_UPDATED, pageUrl } from "@/lib/site";

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
/**
 * The link after a fact (U28: two or three sentences in the cell, the rest one click away). A
 * guide that is not in this language opens in German, marked as such.
 */
function MoreLink({ locale, to, m }: { locale: Locale; to: string; m: Messages }) {
  const labels: Record<string, string> = {
    aufnahme: m.cta.filming,
    "so-funktioniert-es": m.cta.how,
    demo: m.cta.demo,
    preise: m.cta.pricing,
    datenschutz: m.data.privacyLink,
    daten: m.cta.data,
  };
  const guide = to.startsWith("ratgeber/") ? GUIDES.find((g) => `ratgeber/${g.slug}` === to) : undefined;
  const own = !guide || guide.locales.includes(locale);
  const l: Locale = own ? locale : "de";
  const label = guide ? guide.title[l]! : labels[to];
  if (!label) return null;
  return (
    <span className="block">
      <Link href={`/${l}/${to}/`} className="link" hrefLang={own ? undefined : l} lang={own ? undefined : l}>
        {label}
      </Link>
    </span>
  );
}

export default async function Facts({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.facts;
  const rows = factRows(locale);
  const links: [string, string][] = [
    ["so-funktioniert-es", m.nav.how],
    ["aufnahme", m.nav.filming],
    ["preise", m.nav.pricing],
    ["daten", m.nav.data],
    ["ratgeber", m.nav.guides],
    ["ueber-uns", m.nav.us],
    ["hilfe", m.nav.faq],
    // the blog stays reachable here while it is too small for the footer (U28)
    ["blog", m.nav.blog],
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
      <PageHead kick={t.title} title={t.head} lead={t.lead} />
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
                  <td className="block pb-4 leading-[1.55] [overflow-wrap:anywhere] md:table-cell md:pt-4">
                    {r.v.includes("@") ? <a href={`mailto:${r.v}`} className="link">{r.v}</a> : r.v}
                    {r.to && <MoreLink locale={locale} to={r.to} m={m} />}
                  </td>
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
          <h3 className="mt-8 text-[1.5rem]">{t.more}</h3>
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
        <Updated locale={locale} date={PAGE_UPDATED.fakten} />
      </div>
    </KitScope>
  );
}

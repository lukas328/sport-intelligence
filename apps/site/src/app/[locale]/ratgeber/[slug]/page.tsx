import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Crumbs } from "@/components/crumbs";
import { JsonLd } from "@/components/json-ld";
import { KitScope } from "@/components/kit";
import { PageHead, SectionHead } from "@/components/wurf-head";
import { guideModule, mdxComponents } from "@/lib/content";
import { HTML_LANG, fmt, isLocale, messages, type Locale } from "@/lib/i18n";
import { article, breadcrumbs, faqPage, graph, howTo } from "@/lib/schema";
import { pageMeta } from "@/lib/seo";
import { pageUrl } from "@/lib/site";
import { GUIDES, type Guide } from "../../../../../content/ratgeber";

type Props = { params: Promise<{ locale: Locale; slug: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return GUIDES.flatMap((g) => g.locales.map((locale) => ({ locale, slug: g.slug })));
}

function find(locale: string, slug: string): Guide | undefined {
  const g = GUIDES.find((x) => x.slug === slug);
  return g && isLocale(locale) && g.locales.includes(locale) ? g : undefined;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const g = find(locale, slug);
  if (!g) return {};
  return pageMeta(locale, `ratgeber/${slug}`, g.metaTitle[locale], g.description[locale]!, {
    available: g.locales,
    article: { published: g.published, modified: g.updated },
  });
}

/** One guide: the question as title, the answer first, then the steps, short answers, related guides. */
export default async function GuidePage({ params }: Props) {
  const { locale, slug } = await params;
  const g = find(locale, slug);
  if (!g) notFound();
  const m = messages(locale);
  const t = m.guides;
  const mod = await guideModule(locale, slug);
  const Body = mod.default;
  const path = `ratgeber/${slug}`;
  const date = new Intl.DateTimeFormat(HTML_LANG[locale], { dateStyle: "long", timeZone: "Europe/Zurich" });
  const title = g.title[locale]!;
  const answer = g.answer[locale]!;
  const related = g.related.map((s) => GUIDES.find((x) => x.slug === s)).filter((x): x is Guide => Boolean(x));
  return (
    <KitScope>
      <JsonLd
        data={graph(
          article(locale, path, { headline: title, description: g.description[locale]!, published: g.published, modified: g.updated }),
          breadcrumbs([
            [t.home, pageUrl(locale)],
            [t.title, pageUrl(locale, "ratgeber")],
            [title, pageUrl(locale, path)],
          ]),
          mod.faq && faqPage(locale, path, mod.faq),
          mod.howto && howTo(locale, path, mod.howto),
        )}
      />
      <article>
        <PageHead
          kick={
            <Crumbs
              label={m.nav.crumbs}
              items={[
                [t.home, `/${locale}/`],
                [t.title, `/${locale}/ratgeber/`],
              ]}
            />
          }
          title={title}
          lead={answer}
        >
          <p className="mt-5 text-[1.0625rem] text-ink-2">
            <time dateTime={g.updated}>{fmt(t.updated, { date: date.format(new Date(g.updated)) })}</time>
          </p>
        </PageHead>
        <div className="wrap">
          <div className="prose mt-10">
            <Body components={mdxComponents(locale, "ratgeber")} />
          </div>

          {mod.faq && mod.faq.length > 0 && (
            <section aria-labelledby="kurz" className="prose mt-14">
              <h2 id="kurz">{t.faqTitle}</h2>
              {mod.faq.map((f) => (
                <div key={f.q}>
                  <h3>{f.q}</h3>
                  <p>{f.a}</p>
                </div>
              ))}
            </section>
          )}

          <aside aria-labelledby="produkt" className="measure mt-14 border-t-2 border-ink pt-6">
            <h2 id="produkt" className="font-slant text-[1.5rem] md:text-[1.75rem]">
              {t.productTitle}
            </h2>
            <p className="mt-2 leading-[1.6]">{t.productText}</p>
            <div className="mt-2 flex flex-wrap gap-x-8">
              <Link href={`/${locale}/so-funktioniert-es/`} className="link">
                {t.productLink}
              </Link>
              <Link href={`/${locale}/demo/`} className="link">
                {m.cta.demo}
              </Link>
            </div>
          </aside>

          {related.length > 0 && (
            <section aria-labelledby="mehr" className="mt-14">
              <SectionHead id="mehr" title={t.related} />
              <ul className="mt-2 max-w-[48rem]">
                {related.map((r) => {
                  const own = r.locales.includes(locale);
                  const l = own ? locale : "de";
                  return (
                    <li key={r.slug} className="border-b border-rule py-4">
                      <Link href={`/${l}/ratgeber/${r.slug}/`} hrefLang={own ? undefined : "de-CH"} lang={own ? undefined : "de-CH"} className="font-slant text-[1.375rem] hover:underline">
                        {r.title[l]}
                      </Link>
                    </li>
                  );
                })}
              </ul>
              <Link href={`/${locale}/ratgeber/`} className="link mt-4">
                {t.all}
              </Link>
            </section>
          )}
        </div>
      </article>
    </KitScope>
  );
}

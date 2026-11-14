import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Crumbs } from "@/components/crumbs";
import { JsonLd } from "@/components/json-ld";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { KitScope, StartLink } from "@/components/kit";
import { PageHead, SectionHead } from "@/components/wurf-head";
import { guideModule, mdxComponents } from "@/lib/content";
import { APP_LOCALE, HTML_LANG, fmt, isLocale, messages, type Locale } from "@/lib/i18n";
import { headingsOf } from "@/lib/slug";
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
  const source = readFileSync(join(process.cwd(), "content", "ratgeber", locale, `${slug}.mdx`), "utf8");
  const toc = [...headingsOf(source), ...(mod.faq?.length ? [{ id: "kurz", text: t.faqTitle }] : [])];
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
        <div className="wrap grid grid-cols-1 gap-x-14 lg:grid-cols-[minmax(0,1fr)_17rem]">
          <div className="min-w-0">
            {toc.length > 2 && (
              <details className="mt-8 border-y-2 border-ink lg:hidden">
                <summary className="flex min-h-14 items-center justify-between font-bold">{t.toc}</summary>
                <ol className="pb-4">
                  {toc.map((h) => (
                    <li key={h.id}>
                      <a href={`#${h.id}`} className="inline-flex min-h-11 items-center underline-offset-4 hover:underline">
                        {h.text}
                      </a>
                    </li>
                  ))}
                </ol>
              </details>
            )}
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
                        <p className="mt-1 text-ink-2" lang={own ? undefined : "de-CH"}>
                          {r.description[l]}
                        </p>
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

          <aside aria-label={t.toc} className="hidden lg:block">
            <div className="sticky top-6 mt-10">
              {toc.length > 2 && (
                <nav aria-labelledby="toc-title">
                  <h2 id="toc-title" className="font-slant border-b-2 border-ink pb-2 text-[1.375rem]">
                    {t.toc}
                  </h2>
                  <ol className="mt-2">
                    {toc.map((h) => (
                      <li key={h.id} className="border-b border-rule">
                        <a href={`#${h.id}`} className="block py-2.5 text-[1.0625rem] leading-snug underline-offset-4 hover:underline">
                          {h.text}
                        </a>
                      </li>
                    ))}
                  </ol>
                </nav>
              )}
              <div className="mt-8 border-2 border-ink bg-paper p-5">
                <p className="font-slant text-[1.375rem] leading-tight">{m.home.finalTitle}</p>
                <p className="mt-2 text-[1.0625rem]">{t.try}</p>
                <StartLink appLocale={APP_LOCALE[locale]} className="btn btn-ink mt-4 w-full">
                  {m.cta.start}
                </StartLink>
                <Link href={`/${locale}/demo/`} className="link mt-3">
                  {m.cta.demo}
                </Link>
              </div>
            </div>
          </aside>
        </div>
      </article>
    </KitScope>
  );
}

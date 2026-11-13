import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { JsonLd } from "@/components/json-ld";
import { Crumbs } from "@/components/crumbs";
import { article, breadcrumbs, graph } from "@/lib/schema";
import { KitScope } from "@/components/kit";
import { MailLine } from "@/components/mail-line";
import { PageHead } from "@/components/wurf-head";
import { helpBody, mdxComponents } from "@/lib/content";
import { LOCALES, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { SITE_UPDATED, pageUrl } from "@/lib/site";
import { HELP } from "../../../../../content/help";

type Props = { params: Promise<{ locale: Locale; slug: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return LOCALES.flatMap((locale) => HELP.map((h) => ({ locale, slug: h.slug })));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const entry = HELP.find((h) => h.slug === slug);
  if (!entry) return {};
  const meta = pageMeta(locale, `hilfe/${slug}`, entry.title[locale], entry.summary[locale]);
  // guides outside the core stay reachable for the app's links, but out of search engines
  return entry.listed === false ? { ...meta, robots: { index: false } } : meta;
}

export default async function HelpArticle({ params }: Props) {
  const { locale, slug } = await params;
  const entry = HELP.find((h) => h.slug === slug);
  if (!entry) notFound();
  const m = messages(locale);
  const t = m.help;
  const Body = await helpBody(locale, slug);
  return (
    <KitScope>
      <JsonLd
        data={graph(
          article(locale, `hilfe/${slug}`, { headline: entry.title[locale], description: entry.summary[locale], published: SITE_UPDATED, type: "TechArticle" }),
          breadcrumbs([
            [m.guides.home, pageUrl(locale)],
            [m.nav.faq, pageUrl(locale, "hilfe")],
            [entry.title[locale], pageUrl(locale, `hilfe/${slug}`)],
          ]),
        )}
      />
      <PageHead kick={<Crumbs label={m.nav.crumbs} items={[[m.guides.home, `/${locale}/`], [m.nav.faq, `/${locale}/hilfe/`]]} />} title={entry.title[locale]} lead={entry.summary[locale]} />
      <article className="wrap">
        {entry.listed === false && (
          <p role="note" className="measure mt-10 border-l-4 border-ink pl-4 text-ink-2">
            {t.aside}
          </p>
        )}
        <div className="prose mt-10">
          <Body components={mdxComponents(locale, "hilfe")} />
        </div>
        <p className="measure mt-12 border-t-2 border-ink pt-6">
          <b>{t.more}</b> <MailLine template={t.contact} />
        </p>
      </article>
    </KitScope>
  );
}

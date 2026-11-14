import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { KitScope } from "@/components/kit";
import { PageHead } from "@/components/wurf-head";
import { JsonLd } from "@/components/json-ld";
import { Crumbs } from "@/components/crumbs";
import { article, breadcrumbs, graph } from "@/lib/schema";
import { blogBody, mdxComponents } from "@/lib/content";
import { HTML_LANG, LOCALES, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { pageUrl } from "@/lib/site";
import { BLOG } from "../../../../../content/blog";
import { GUIDES } from "../../../../../content/ratgeber";
import Link from "next/link";

type Props = { params: Promise<{ locale: Locale; slug: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return LOCALES.flatMap((locale) => BLOG.map((p) => ({ locale, slug: p.slug })));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const post = BLOG.find((p) => p.slug === slug);
  if (!post) return {};
  // merged into a guide: not indexed, canonical on the guide (the host should answer with a 301)
  if (post.movedTo) return { title: post.title[locale], robots: { index: false, follow: true }, alternates: { canonical: pageUrl(locale, post.movedTo) } };
  return pageMeta(locale, `blog/${slug}`, post.title[locale], post.summary[locale], { article: { published: post.date, modified: post.updated } });
}

export default async function BlogPost({ params }: Props) {
  const { locale, slug } = await params;
  const post = BLOG.find((p) => p.slug === slug);
  if (!post) notFound();
  if (post.movedTo) {
    const target = `/${locale}/${post.movedTo}/`;
    const moved = messages(locale).moved;
    return (
      <div className="wrap py-16">
        <meta httpEquiv="refresh" content={`0; url=${target}`} />
        <h1 className="text-[2.5rem]">{moved.title}</h1>
        <Link href={target} className="link mt-4">
          {moved.text.replace("{page}", GUIDES.find((g) => `ratgeber/${g.slug}` === post.movedTo)?.title[locale] ?? target)}
        </Link>
      </div>
    );
  }
  const m = messages(locale);
  const Body = await blogBody(locale, slug);
  const date = new Intl.DateTimeFormat(HTML_LANG[locale], { dateStyle: "long", timeZone: "Europe/Zurich" });
  return (
    <KitScope>
    <article>
      <JsonLd
        data={graph(
          article(locale, `blog/${slug}`, { headline: post.title[locale], description: post.summary[locale], published: post.date, modified: post.updated, type: "BlogPosting" }),
          breadcrumbs([
            [m.guides.home, pageUrl(locale)],
            [m.blog.title, pageUrl(locale, "blog")],
            [post.title[locale], pageUrl(locale, `blog/${slug}`)],
          ]),
        )}
      />
      <PageHead
        kick={<Crumbs label={m.nav.crumbs} items={[[m.guides.home, `/${locale}/`], [m.blog.title, `/${locale}/blog/`]]} />}
        title={post.title[locale]}
        lead={<time dateTime={post.date}>{date.format(new Date(post.date))}</time>}
      />
      <div className="wrap">
        <div className="prose mt-10">
          <Body components={mdxComponents(locale, "blog")} />
        </div>
      </div>
    </article>
    </KitScope>
  );
}

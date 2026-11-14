import type { Metadata } from "next";
import Link from "next/link";
import { KitScope } from "@/components/kit";
import { PageHead } from "@/components/wurf-head";
import { HTML_LANG, messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { BLOG } from "../../../../content/blog";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMeta(locale, "blog", messages(locale).seo.blog.title, messages(locale).seo.blog.description);
}

export default async function Blog({ params }: Props) {
  const { locale } = await params;
  const t = messages(locale).blog;
  const date = new Intl.DateTimeFormat(HTML_LANG[locale], { dateStyle: "long", timeZone: "Europe/Zurich" });
  const posts = BLOG.filter((p) => !p.movedTo).sort((a, b) => b.date.localeCompare(a.date));
  return (
    <KitScope>
      <PageHead kick={t.title} title={t.head} />
      <div className="wrap">
        <ul className="mt-12 max-w-[48rem] border-t-2 border-ink">
          {posts.map((p) => (
            <li key={p.slug} className="border-b border-rule py-8">
              <time dateTime={p.date} className="text-[1.0625rem] text-ink-2">
                {date.format(new Date(p.date))}
              </time>
              <h2 className="mt-2 text-[2rem]">
                <Link href={`/${locale}/blog/${p.slug}/`} className="underline decoration-2 underline-offset-[6px] hover:decoration-[3px]">
                  {p.title[locale]}
                </Link>
              </h2>
              <p className="measure mt-3">{p.summary[locale]}</p>
            </li>
          ))}
        </ul>
      </div>
    </KitScope>
  );
}

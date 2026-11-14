import type { Metadata } from "next";
import Link from "next/link";
import { ToolPage } from "@/components/tool-page";
import { messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).tools.templates;
  return pageMeta(locale, "vorlagen", t.metaTitle, t.description);
}

export default async function Templates({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.tools;
  const items: [string, string, string][] = [
    [`/${locale}/vorlagen/einwilligung/`, t.consent.title, t.consent.lead],
    [`/${locale}/vorlagen/strichliste/`, t.tally.title, t.tally.lead],
    [`/${locale}/vorlagen/spieltag/`, t.matchday.title, t.matchday.lead],
    [`/${locale}/aufnahme/#notice`, t.templates.notice, t.templates.noticeText],
  ];
  return (
    <ToolPage locale={locale} path="vorlagen" title={t.templates.head.replace(/\.$/, "")} description={t.templates.description} lead={t.templates.lead}>
      <ul className="mt-10 max-w-[52rem] border-t-2 border-ink">
        {items.map(([href, title, text]) => (
          <li key={href} className="border-b border-rule py-5">
            <Link href={href} className="font-slant text-[1.5rem] leading-tight hover:underline md:text-[1.625rem]">
              {title}
            </Link>
            <p className="measure mt-1 text-ink-2">{text}</p>
          </li>
        ))}
      </ul>
    </ToolPage>
  );
}

import type { Metadata } from "next";
import Link from "next/link";
import { KitScope } from "@/components/kit";
import { PageHead, SectionHead } from "@/components/wurf-head";
import { messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { STATUS_URL, SUPPORT_EMAIL } from "@/lib/site";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMeta(locale, "kontakt", messages(locale).seo.about.title, messages(locale).seo.about.description);
}

export default async function About({ params }: Props) {
  const { locale } = await params;
  const t = messages(locale).about;
  return (
    <KitScope>
      <PageHead kick={t.title} title={t.head} />
      <div className="wrap">
        <section aria-labelledby="contact" className="mt-12">
          <SectionHead id="contact" title={t.contactTitle} />
          <p className="mt-6 text-ink-2">{t.email}</p>
          <a href={`mailto:${SUPPORT_EMAIL}`} className="font-slant inline-flex min-h-12 items-center text-[1.75rem] break-all underline decoration-2 underline-offset-[6px] md:text-[2.5rem]">
            {SUPPORT_EMAIL}
          </a>
          <p className="measure mt-4">{t.reply}</p>
          <p className="measure mt-2 text-ink-2">{t.inApp}</p>
          {STATUS_URL && (
            <a href={STATUS_URL} className="link mt-2">
              {t.status}
            </a>
          )}
        </section>
        <section aria-labelledby="who" className="mt-16">
          <SectionHead id="who" title={t.whoTitle} />
          <p className="measure mt-4">{t.who}</p>
          <Link href={`/${locale}/ueber-uns/`} className="link mt-2">
            {messages(locale).nav.us}
          </Link>
        </section>
      </div>
    </KitScope>
  );
}

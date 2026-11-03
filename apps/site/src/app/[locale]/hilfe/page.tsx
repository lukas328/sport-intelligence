import type { Metadata } from "next";
import { HelpSearch } from "@/components/help-search";
import { messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { SUPPORT_EMAIL } from "@/lib/site";
import { fmt } from "@/lib/i18n";
import { HELP } from "../../../../content/help";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).help;
  return pageMeta(locale, "hilfe", t.title, t.lead);
}

export default async function Help({ params }: Props) {
  const { locale } = await params;
  const t = messages(locale).help;
  return (
    <>
      <h1 className="text-3xl font-bold">{t.title}</h1>
      <p className="mt-3 max-w-2xl text-lg text-muted">{t.lead}</p>
      <HelpSearch entries={HELP} locale={locale} t={t} />
      <p className="mt-12 text-sm text-muted">
        {t.more} {fmt(t.contact, { email: SUPPORT_EMAIL })}
      </p>
    </>
  );
}

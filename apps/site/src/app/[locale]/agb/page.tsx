import type { Metadata } from "next";
import { LegalPage } from "@/components/legal-page";
import { messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const m = messages(locale);
  return pageMeta(locale, "agb", m.seo.terms.title, m.seo.terms.description);
}

export default async function Page({ params }: Props) {
  const { locale } = await params;
  return <LegalPage locale={locale} page="agb" />;
}

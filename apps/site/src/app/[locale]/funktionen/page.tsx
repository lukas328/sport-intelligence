import type { Metadata } from "next";
import Link from "next/link";
import { messages, type Locale } from "@/lib/i18n";
import { pageUrl } from "@/lib/site";

type Props = { params: Promise<{ locale: Locale }> };

/** The old features page moved to «So funktioniert es»; old links land there (static: meta refresh). */
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return { title: messages(locale).moved.title, robots: { index: false }, alternates: { canonical: pageUrl(locale, "so-funktioniert-es") } };
}

export default async function Moved({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const target = `/${locale}/so-funktioniert-es/`;
  return (
    <div className="wrap py-16">
      <meta httpEquiv="refresh" content={`0; url=${target}`} />
      <h1 className="text-[2.5rem]">{m.moved.title}</h1>
      <Link href={target} className="link mt-4">
        {m.moved.text.replace("{page}", m.nav.how)}
      </Link>
    </div>
  );
}

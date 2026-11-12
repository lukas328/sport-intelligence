import type { Metadata } from "next";
import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import { Footer } from "@/components/footer";
import { Header } from "@/components/header";
import { HTML_LANG, isLocale, localeParams, messages } from "@/lib/i18n";
import { SITE_URL } from "@/lib/site";
import localFont from "next/font/local";
import "../globals.css";

// same typeface as the app (SIL OFL, src/fonts/OFL.txt)
const archivo = localFont({
  src: "../../fonts/archivo-variable.woff2",
  variable: "--font-archivo",
  display: "swap",
  weight: "100 900",
  declarations: [{ prop: "font-stretch", value: "62% 125%" }],
});

export const dynamicParams = false;
export const generateStaticParams = localeParams;

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).meta;
  return {
    metadataBase: new URL(SITE_URL),
    title: { default: t.title, template: `%s | Handball Intelligence` },
    description: t.description,
    icons: { icon: [{ url: "/favicon.svg", type: "image/svg+xml" }, { url: "/icon.png", sizes: "192x192" }], apple: "/apple-icon.png" },
    openGraph: {
      siteName: "Handball Intelligence",
      type: "website",
      locale: HTML_LANG[isLocale(locale) ? locale : "de"],
      images: [{ url: "/og.png", width: 1200, height: 630, alt: "Handball Intelligence" }],
    },
  };
}

export default async function LocaleLayout({ children, params }: { children: ReactNode; params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  return (
    <html lang={HTML_LANG[locale]} className={archivo.variable}>
      <body className="min-h-screen antialiased">
        <Header locale={locale} />
        <main id="main" className="mx-auto max-w-6xl px-4 py-10">
          {children}
        </main>
        <Footer locale={locale} />
      </body>
    </html>
  );
}

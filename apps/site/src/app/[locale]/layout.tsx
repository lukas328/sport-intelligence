import type { Metadata } from "next";
import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import { Footer } from "@/components/footer";
import { Header } from "@/components/header";
import { HTML_LANG, isLocale, localeParams, messages } from "@/lib/i18n";
import { SITE_URL } from "@/lib/site";
import localFont from "next/font/local";
import "../globals.css";

// the app's typefaces (Anlauf), self-hosted, SIL OFL: src/fonts/OFL-*.txt
const kanit = localFont({
  src: [
    { path: "../../fonts/kanit-latin-800-italic.woff2", weight: "800", style: "italic" },
    { path: "../../fonts/kanit-latin-900-italic.woff2", weight: "900", style: "italic" },
  ],
  variable: "--font-kanit",
  display: "swap",
});
const hanken = localFont({
  src: "../../fonts/hanken-grotesk-latin-wght-normal.woff2",
  weight: "100 900",
  style: "normal",
  variable: "--font-hanken",
  display: "swap",
});
const plexMono = localFont({
  src: [
    { path: "../../fonts/ibm-plex-mono-latin-500-normal.woff2", weight: "500" },
    { path: "../../fonts/ibm-plex-mono-latin-600-normal.woff2", weight: "600" },
  ],
  variable: "--font-plex-mono",
  display: "swap",
  preload: false,
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
    icons: { icon: [{ url: "/favicon.svg", type: "image/svg+xml" }, { url: "/icon.png", sizes: "512x512" }], apple: "/apple-icon.png" },
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
    <html lang={HTML_LANG[locale]} className={`${kanit.variable} ${hanken.variable} ${plexMono.variable}`}>
      <body className="min-h-screen">
        <Header locale={locale} />
        <main id="main" tabIndex={-1} className="outline-none">
          {children}
        </main>
        <Footer locale={locale} />
      </body>
    </html>
  );
}

import { ConsentBanner } from "@/components/consent-banner";
import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import "./globals.css";
import { Providers } from "./providers";

// Kanit (slanted: titles, numerals, names, navigation), Hanken Grotesk (text) and IBM Plex Mono
// (times on the tactics camera), all SIL OFL (licences in src/fonts). Self-hosted, no request to
// a font service; only the cuts in use are shipped.
const kanit = localFont({
  src: [
    { path: "../fonts/kanit-latin-700-italic.woff2", weight: "700", style: "italic" },
    { path: "../fonts/kanit-latin-800-italic.woff2", weight: "800", style: "italic" },
    { path: "../fonts/kanit-latin-900-italic.woff2", weight: "900", style: "italic" },
  ],
  variable: "--font-kanit",
  display: "swap",
});
const hanken = localFont({
  src: "../fonts/hanken-grotesk-latin-wght-normal.woff2",
  weight: "100 900",
  style: "normal",
  variable: "--font-hanken",
  display: "swap",
});
const plexMono = localFont({
  src: [
    { path: "../fonts/ibm-plex-mono-latin-500-normal.woff2", weight: "500" },
    { path: "../fonts/ibm-plex-mono-latin-600-normal.woff2", weight: "600" },
  ],
  variable: "--font-plex-mono",
  display: "swap",
  preload: false,
});

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("app");
  return { title: { default: t("name"), template: `%s · ${t("name")}` }, description: t("description") };
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#eceae5",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const locale = await getLocale();
  return (
    <html lang={locale} className={`${kanit.variable} ${hanken.variable} ${plexMono.variable}`} suppressHydrationWarning>
      <body className="min-h-dvh antialiased">
        <NextIntlClientProvider>
          <Providers>
            {children}
            <ConsentBanner />
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}

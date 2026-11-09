import { ConsentBanner } from "@/components/consent-banner";
import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import { NextIntlClientProvider } from "next-intl";
import { cookies } from "next/headers";
import { getLocale, getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import "./globals.css";
import { Providers } from "./providers";

// Barlow and Barlow Condensed (SIL OFL, src/fonts): the text cut for reading, the condensed cut
// for headings and scores, like a match sheet. Reenie Beanie only shows real coach notes.
// Self-hosted, no request to a font service; only the cuts in use are shipped.
const barlow = localFont({
  src: [
    { path: "../fonts/barlow-latin-400-normal.woff2", weight: "400" },
    { path: "../fonts/barlow-latin-500-normal.woff2", weight: "500" },
    { path: "../fonts/barlow-latin-600-normal.woff2", weight: "600" },
    { path: "../fonts/barlow-latin-700-normal.woff2", weight: "700" },
  ],
  variable: "--font-barlow",
  display: "swap",
});
const barlowCondensed = localFont({
  src: [
    { path: "../fonts/barlow-condensed-latin-600-normal.woff2", weight: "600" },
    { path: "../fonts/barlow-condensed-latin-700-normal.woff2", weight: "700" },
    { path: "../fonts/barlow-condensed-latin-800-normal.woff2", weight: "800" },
  ],
  variable: "--font-barlow-condensed",
  display: "swap",
});
const reenie = localFont({
  src: "../fonts/reenie-beanie-latin-400-normal.woff2",
  variable: "--font-reenie",
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
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#eef5fb" },
    { media: "(prefers-color-scheme: dark)", color: "#07131f" },
  ],
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const locale = await getLocale();
  const theme = (await cookies()).get("hb_theme")?.value;
  return (
    <html lang={locale} className={`${barlow.variable} ${barlowCondensed.variable} ${reenie.variable}`} data-theme={theme === "light" || theme === "dark" ? theme : undefined} suppressHydrationWarning>
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

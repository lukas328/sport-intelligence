import type { Metadata, Viewport } from "next";
import Link from "next/link";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import "./globals.css";
import { Providers } from "./providers";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("app");
  return { title: { default: t("name"), template: `%s · ${t("name")}` }, description: t("description") };
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0b1120" },
  ],
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const locale = await getLocale();
  const t = await getTranslations();
  return (
    <html lang={locale}>
      <body className="min-h-dvh antialiased">
        <NextIntlClientProvider>
          <Providers>
            <header className="border-b border-border">
              <nav
                aria-label="Hauptnavigation"
                className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3"
              >
                <Link href="/" className="font-semibold tracking-tight">
                  {t("app.name")}
                </Link>
                <Link href="/status" className="text-sm text-muted hover:text-foreground">
                  {t("nav.status")}
                </Link>
              </nav>
            </header>
            <main className="mx-auto max-w-5xl px-4 py-10">{children}</main>
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}

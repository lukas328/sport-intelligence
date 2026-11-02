import type { Metadata, Viewport } from "next";
import Link from "next/link";
import { NextIntlClientProvider } from "next-intl";
import { cookies } from "next/headers";
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
  const signedIn = Boolean((await cookies()).get("hb_session"));
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
                <div className="flex items-center gap-4 text-sm">
                  <Link href="/status" className="text-muted hover:text-foreground">
                    {t("nav.status")}
                  </Link>
                  <Link href={signedIn ? "/app" : "/login"} className="font-medium text-accent">
                    {signedIn ? t("nav.app") : t("nav.login")}
                  </Link>
                </div>
              </nav>
            </header>
            <main className="mx-auto max-w-5xl px-4 py-10">{children}</main>
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}

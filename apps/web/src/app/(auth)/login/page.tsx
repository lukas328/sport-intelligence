import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { OAuthButtons } from "@/components/oauth-buttons";
import { fetchProviders } from "@/lib/api";
import { safeNext } from "@/lib/nav";
import { LoginForm } from "./login-form";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("auth"))("loginTitle") };
}

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string; totp?: string }> }) {
  const { next, totp } = await searchParams;
  const providers = totp ? [] : await fetchProviders();
  return (
    <Suspense>
      <LoginForm oauth={<OAuthButtons providers={providers} next={safeNext(next)} />} />
    </Suspense>
  );
}

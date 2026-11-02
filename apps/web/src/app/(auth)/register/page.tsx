import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { serverApi } from "@/lib/api";
import { RegisterForm } from "./register-form";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("auth"))("registerTitle") };
}

export default async function RegisterPage({ searchParams }: { searchParams: Promise<{ invite?: string }> }) {
  const { invite } = await searchParams;
  let email: string | undefined;
  if (invite) {
    const { data } = await (await serverApi()).GET("/v1/invitations/{token}", { params: { path: { token: invite } } });
    email = data?.status === "pending" ? data.email : undefined;
  }
  return <RegisterForm invitationToken={email ? invite : undefined} email={email} />;
}

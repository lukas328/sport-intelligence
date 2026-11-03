import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { serverApi } from "@/lib/api";
import { JoinView } from "./join-view";

export const metadata: Metadata = { title: "Verband", robots: { index: false } };

export default async function JoinPage({ searchParams }: { searchParams: Promise<{ token?: string }> }) {
  const { token } = await searchParams;
  const { data: me } = await (await serverApi()).GET("/v1/me");
  if (!me) redirect(`/login?next=${encodeURIComponent(`/federation/join?token=${token ?? ""}`)}`);
  const orgs = me.organizations.filter((o) => o.role === "org_admin");
  return <JoinView token={token ?? ""} orgs={orgs} />;
}

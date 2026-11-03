import { notFound, redirect } from "next/navigation";
import { serverApi } from "@/lib/api";
import { OpsView } from "./ops-view";

export const metadata = { title: "Backoffice", robots: { index: false } };

export default async function OpsPage() {
  const client = await serverApi();
  const me = await client.GET("/v1/ops/me");
  if (me.response.status === 401) redirect("/login?next=/ops");
  if (!me.data) notFound();
  return <OpsView />;
}

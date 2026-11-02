import { redirect } from "next/navigation";
import { serverApi } from "@/lib/api";

export default async function AppIndex() {
  const { data: me } = await (await serverApi()).GET("/v1/me");
  if (!me) redirect("/login");
  const first = me.organizations[0];
  redirect(first ? `/app/${first.id}` : "/onboarding");
}

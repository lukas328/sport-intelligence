import { redirect } from "next/navigation";
import { settingsTarget } from "@/lib/settings-model";
import { loadSettings } from "./load";

/** Old single settings page: split into "Ich" and "Verein" (SPEC section 6). */
export default async function SettingsPage({ params, searchParams }: { params: Promise<{ orgId: string }>; searchParams: Promise<{ section?: string }> }) {
  const { orgId } = await params;
  const { isAdmin } = await loadSettings(orgId);
  redirect(settingsTarget(orgId, isAdmin, (await searchParams).section));
}

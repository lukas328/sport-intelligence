import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import type { CSSProperties, ReactNode } from "react";
import { LogoutButton } from "@/components/logout-button";
import { SupportBar } from "@/components/support/support-bar";
import { NotificationBell } from "@/components/training/bell";
import { serverApi } from "@/lib/api";
import { accentFor } from "@/lib/color";

export default async function OrgLayout({ children, params }: { children: ReactNode; params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  const t = await getTranslations();
  const { data: org, response } = await (await serverApi()).GET("/v1/orgs/{org_id}", {
    params: { path: { org_id: orgId } },
  });
  if (response.status === 401) redirect(`/login?next=/app/${orgId}`);
  if (!org) notFound();
  const { accent, contrast } = accentFor(org.primary_color);
  const style = { "--accent": accent, "--accent-contrast": contrast } as CSSProperties;
  return (
    <div style={style} className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
        <Link href={`/app/${org.id}`} className="flex items-center gap-3">
          {org.has_logo ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={`/v1/orgs/${org.id}/logo`} alt="" className="size-10 rounded object-contain" />
          ) : (
            <span aria-hidden className="size-10 rounded" style={{ background: org.primary_color }} />
          )}
          <span className="text-lg font-semibold">{org.name}</span>
        </Link>
        <nav aria-label={org.name} className="flex flex-wrap items-center gap-1 text-sm">
          <Link href={`/app/${org.id}`} className="rounded px-3 py-2 hover:bg-surface">
            {t("common.teams")}
          </Link>
          <Link href={`/app/${org.id}/assignments`} className="rounded px-3 py-2 hover:bg-surface">
            {t("nav.assignments")}
          </Link>
          <Link href={`/app/${org.id}/drills`} className="rounded px-3 py-2 hover:bg-surface">
            {t("nav.drills")}
          </Link>
          <Link href={`/app/${org.id}/feed`} className="rounded px-3 py-2 hover:bg-surface">
            {t("nav.feed")}
          </Link>
          <Link href={`/app/${org.id}/schedule`} className="rounded px-3 py-2 hover:bg-surface">
            {t("schedule.nav")}
          </Link>
          <Link href={`/app/${org.id}/profile`} className="rounded px-3 py-2 hover:bg-surface">
            {t("profile.nav")}
          </Link>
          <Link href={`/app/${org.id}/consents`} className="rounded px-3 py-2 hover:bg-surface">
            {t("nav.consents")}
          </Link>
          <Link href={`/app/${org.id}/settings`} className="rounded px-3 py-2 hover:bg-surface">
            {t("common.settings")}
          </Link>
          <SupportBar orgId={org.id} />
          <NotificationBell orgId={org.id} />
          <LogoutButton />
        </nav>
      </div>
      {org.two_factor_required && (
        <p role="status" className="rounded-md border-l-4 border-accent bg-surface px-4 py-2 text-sm">
          {t("settings.twoFactorRequired")}{" "}
          <Link href={`/app/${org.id}/settings#security`} className="underline underline-offset-4">
            {t("settings.twoFactorStart")}
          </Link>
        </p>
      )}
      {children}
    </div>
  );
}

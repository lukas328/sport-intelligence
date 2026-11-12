import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { cookies } from "next/headers";
import { getTranslations } from "next-intl/server";
import type { CSSProperties, ReactNode } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { TwoFactorBanner } from "@/components/shell/two-factor-banner";
import { serverApi } from "@/lib/api";
import { CHECK_KITS, clubStyle } from "@/lib/color";

export default async function OrgLayout({ children, params }: { children: ReactNode; params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  const t = await getTranslations();
  const client = await serverApi();
  const [{ data: org, response }, { data: me }, { data: teams = [] }] = await Promise.all([
    client.GET("/v1/orgs/{org_id}", { params: { path: { org_id: orgId } } }),
    client.GET("/v1/me"),
    client.GET("/v1/orgs/{org_id}/teams", { params: { path: { org_id: orgId } } }),
  ]);
  if (response.status === 401) redirect(`/login?next=/app/${orgId}`);
  if (!org || !me) notFound();
  const jar = await cookies();
  const savedTeam = jar.get("hb_team")?.value ?? null;
  // development only: show the club in one of the six check colours (screenshots, SPEC.md 13)
  const preview = process.env.NODE_ENV !== "production" ? CHECK_KITS[jar.get("hb_dev_kit")?.value as keyof typeof CHECK_KITS] : undefined;
  const kitColours = preview ?? ([org.primary_color, org.secondary_color] as const);
  // only while the admin has not set it up yet
  // a club taken over from the official data and not confirmed yet: one quiet line for its admins
  const unverified = org.my_role === "org_admin" && org.verification === "unverified";
  const banner =
    org.two_factor_required && !me.totp_enabled ? (
      <TwoFactorBanner orgId={org.id} />
    ) : unverified ? (
      <p className="px-4 py-2 text-sm text-muted shadow-[inset_0_-1px_0_var(--border)] sm:px-6 lg:px-10" data-testid="unverified-line">
        {t("verification.line")}{" "}
        <Link href={`/app/${org.id}/club/federation`} className="font-medium text-foreground underline underline-offset-4">
          {t("verification.lineLink")}
        </Link>
      </p>
    ) : null;
  return (
    <div className="club min-h-dvh" style={clubStyle(kitColours[0], kitColours[1]) as CSSProperties}>
      <AppShell
        clubVars={clubStyle(kitColours[0], kitColours[1])}
        org={{ id: org.id, name: org.name, has_logo: org.has_logo, primary_color: kitColours[0], secondary_color: kitColours[1], my_role: org.my_role }}
        orgs={me.organizations.map((o) => ({ id: o.id, name: o.name }))}
        teams={teams.map((x) => ({
          id: x.id,
          name: x.name,
          my_role: x.my_role,
          is_youth: x.is_youth,
          season: x.current_season ? t("roster.season", { label: x.current_season.label }) : null,
          season_id: x.current_season?.id ?? null,
          team_features: x.settings.team_features ?? false,
        }))}
        me={{ name: me.name, email: me.email }}
        savedTeam={savedTeam}
        banner={banner}
      >
        {children}
      </AppShell>
    </div>
  );
}

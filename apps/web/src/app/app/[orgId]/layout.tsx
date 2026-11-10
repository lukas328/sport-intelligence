import { notFound, redirect } from "next/navigation";
import { cookies } from "next/headers";
import { getTranslations } from "next-intl/server";
import type { CSSProperties, ReactNode } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { TwoFactorBanner } from "@/components/shell/two-factor-banner";
import { serverApi } from "@/lib/api";
import { clubStyle } from "@/lib/color";

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
  const savedTeam = (await cookies()).get("hb_team")?.value ?? null;
  // only while the admin has not set it up yet
  const banner = org.two_factor_required && !me.totp_enabled ? <TwoFactorBanner orgId={org.id} /> : null;
  return (
    <div className="club min-h-dvh" style={clubStyle(org.primary_color) as CSSProperties}>
      <AppShell
        clubVars={clubStyle(org.primary_color)}
        org={{ id: org.id, name: org.name, has_logo: org.has_logo, primary_color: org.primary_color, my_role: org.my_role }}
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

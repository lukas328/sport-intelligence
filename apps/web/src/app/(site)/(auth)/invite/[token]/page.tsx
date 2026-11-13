import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Alert } from "@/components/ui/card";
import { serverApi } from "@/lib/api";
import { AcceptButton } from "./accept-button";

export default async function InvitePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const t = await getTranslations();
  const client = await serverApi();
  const [{ data: inv }, { data: me }] = await Promise.all([
    client.GET("/v1/invitations/{token}", { params: { path: { token } } }),
    client.GET("/v1/me"),
  ]);
  if (!inv) {
    return (
      <div className="border-t-2 border-ink pt-6">
        <Alert>{t("invite.notFound")}</Alert>
      </div>
    );
  }
  const role = inv.team_role ?? inv.org_role;
  return (
    <div className="space-y-4 border-t-2 border-ink pt-6">
      <h1 className="text-2xl font-bold sm:text-[1.75rem]">{t("invite.title")}</h1>
      <p>{t("invite.intro", { org: inv.organization_name })}</p>
      <ul className="space-y-1 text-sm text-muted">
        {inv.team_name && <li>{t("invite.team", { team: inv.team_name })}</li>}
        <li>{t("invite.role", { role: t(`roles.${role}`) })}</li>
        <li>{t("invite.forEmail", { email: inv.email })}</li>
      </ul>
      {inv.status !== "pending" ? (
        <Alert>{t(`invite.status_${inv.status as "accepted" | "revoked" | "expired"}`)}</Alert>
      ) : me ? (
        <AcceptButton token={token} />
      ) : (
        <div className="flex flex-col gap-2">
          <Link
            href={inv.account_exists ? `/login?next=/invite/${token}` : `/register?invite=${token}`}
            className="inline-flex min-h-10 items-center justify-center bg-accent px-4 py-2 text-sm font-medium text-accent-contrast"
          >
            {inv.account_exists ? t("invite.login") : t("invite.register")}
          </Link>
        </div>
      )}
    </div>
  );
}

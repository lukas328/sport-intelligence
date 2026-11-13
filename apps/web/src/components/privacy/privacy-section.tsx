"use client";

import { problemCode } from "@handball/api-client";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { useConfirm } from "@/components/ui/confirm";

/** Personal data download, account deletion and (for club admins) club deletion (M9). */
export function PrivacySection({ orgId, orgName, isAdmin, hasPassword }: { orgId: string; orgName: string; isAdmin: boolean; hasPassword: boolean }) {
  const t = useTranslations("privacy");
  const [problem, setProblem] = useState<string | null>(null);
  const confirm = useConfirm();

  async function deleteAccount(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    if (!(await confirm({ title: t("accountConfirm"), danger: true }))) return;
    const { error } = await api.POST("/v1/me/delete", {
      body: { confirm_email: String(f.get("email") ?? ""), password: String(f.get("password") ?? "") || null },
    });
    if (error) return setProblem(problemCode(error) ?? "generic");
    window.location.assign("/");
  }
  async function deleteClub(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    if (!(await confirm({ title: t("clubConfirm"), danger: true }))) return;
    const { error } = await api.POST("/v1/orgs/{org_id}/delete", {
      params: { path: { org_id: orgId } },
      body: { confirm_name: String(f.get("name") ?? "") },
    });
    if (error) return setProblem(problemCode(error) ?? "generic");
    window.location.assign("/app");
  }
  const messages: Record<string, string> = {
    "last-admin": t("lastAdmin"),
    "subscription-active": t("subscriptionActive"),
    "confirmation-mismatch": t("mismatch"),
    "invalid-credentials": t("wrongPassword"),
  };
  return (
    <section id="privacy" aria-labelledby="privacy-title" className="space-y-3">
      <h2 id="privacy-title" className="text-lg font-semibold">
        {t("title")}
      </h2>
      <div className="border-t border-foreground/15 pt-5 space-y-4">
        <div className="space-y-2">
          <p className="text-sm">{t("exportHint")}</p>
          {/* eslint-disable-next-line @next/next/no-html-link-for-pages -- API download, not a page */}
          <a href="/v1/me/export" className="inline-flex min-h-9 items-center gap-1.5 bg-raised px-4 text-[0.9375rem] font-medium ring-1 ring-inset ring-border hover:bg-surface" data-testid="export">
            {t("export")}
          </a>
        </div>
        <details>
          <summary className="cursor-pointer text-sm font-medium">{t("deleteAccount")}</summary>
          <form onSubmit={deleteAccount} className="mt-3 max-w-md space-y-3" aria-label={t("deleteAccount")}>
            <p className="text-sm text-muted">{t("accountHint")}</p>
            <Input label={t("email")} name="email" type="email" required autoComplete="off" />
            {hasPassword && <Input label={t("password")} name="password" type="password" required autoComplete="current-password" />}
            <Button type="submit" variant="danger">
              {t("deleteAccount")}
            </Button>
          </form>
        </details>
        {isAdmin && (
          <details>
            <summary className="cursor-pointer text-sm font-medium">{t("deleteClub")}</summary>
            <form onSubmit={deleteClub} className="mt-3 max-w-md space-y-3" aria-label={t("deleteClub")}>
              <p className="text-sm text-muted">{t("clubHint", { name: orgName })}</p>
              <Input label={t("clubName")} name="name" required autoComplete="off" />
              <Button type="submit" variant="danger">
                {t("deleteClub")}
              </Button>
            </form>
          </details>
        )}
        {problem && <Alert>{messages[problem] ?? t("failed")}</Alert>}
      </div>
    </section>
  );
}

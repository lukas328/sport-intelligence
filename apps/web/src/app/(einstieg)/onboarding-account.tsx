"use client";

import { problemCode } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { LogOut, ShieldCheck, Trash2 } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { initials } from "@/components/shell/account-menu";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { DialogContent, DialogRoot } from "@/components/ui/dialog";
import { Input } from "@/components/ui/field";
import { MenuContent, MenuItem, MenuRoot, MenuSeparator, MenuTrigger } from "@/components/ui/menu";
import { api } from "@/lib/client";
import { sitePage, useSiteConfig } from "@/lib/site-config";

/**
 * The account on the onboarding (finding L7): also without a club (after «Verein löschen», or
 * before the first team) there is a way out: Abmelden, Konto löschen, Datenschutz. «Abbrechen»
 * leads into the app only for someone who has a club there.
 */
export function OnboardingAccount() {
  const t = useTranslations("onboardingAccount");
  const tc = useTranslations("common");
  const locale = useLocale();
  const site = useSiteConfig();
  const [del, setDel] = useState(false);
  const me = useQuery({ queryKey: ["me"], queryFn: async () => (await api.GET("/v1/me")).data ?? null });
  if (!me.data) return null;
  const user = me.data;
  return (
    <span className="flex items-center gap-3">
      {user.organizations.length > 0 && (
        <Link href="/app" className="min-h-11 content-center text-[15px] font-bold text-ink underline decoration-[1.5px] underline-offset-4">
          {t("cancel")}
        </Link>
      )}
      <MenuRoot>
        <MenuTrigger aria-label={`${t("account")}: ${user.name}`} data-testid="onboarding-account" className="grid min-h-11 min-w-11 cursor-pointer place-items-center">
          <span aria-hidden className="font-slant grid size-9 place-items-center bg-ink text-[15px] text-ground">
            {initials(user.name) || "?"}
          </span>
        </MenuTrigger>
        <MenuContent align="end" className="w-72">
          <div className="px-3 pt-2 pb-2.5">
            <p className="m-0 truncate text-[15px] font-bold">{user.name}</p>
            <p className="m-0 truncate text-[14px] text-ink-2">{user.email}</p>
          </div>
          <MenuSeparator />
          <MenuItem href={sitePage(site?.site_url, locale, "datenschutz")} external icon={<ShieldCheck />}>
            {t("privacy")}
          </MenuItem>
          <MenuItem
            icon={<LogOut />}
            testId="onboarding-logout"
            onSelect={async () => {
              await api.POST("/v1/auth/logout");
              window.location.assign("/login?out=1");
            }}
          >
            {tc("logout")}
          </MenuItem>
          {/* the destructive entry last, red, with room above it (A1) */}
          <MenuSeparator />
          <MenuItem onSelect={() => setDel(true)} icon={<Trash2 />} danger testId="onboarding-delete">
            {t("delete")}
          </MenuItem>
        </MenuContent>
      </MenuRoot>
      <DeleteAccount open={del} onOpenChange={setDel} hasPassword={user.has_password} />
    </span>
  );
}

function DeleteAccount({ open, onOpenChange, hasPassword }: { open: boolean; onOpenChange: (o: boolean) => void; hasPassword: boolean }) {
  const t = useTranslations("privacy");
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const messages: Record<string, string> = {
    "last-admin": t("lastAdmin"),
    "subscription-active": t("subscriptionActive"),
    "confirmation-mismatch": t("mismatch"),
    "invalid-credentials": t("wrongPassword"),
  };
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    const { error } = await api.POST("/v1/me/delete", {
      body: { confirm_email: String(f.get("email") ?? ""), password: String(f.get("password") ?? "") || null },
    });
    setBusy(false);
    if (error) return setProblem(problemCode(error) ?? "generic");
    window.location.assign("/");
  }
  return (
    <DialogRoot open={open} onOpenChange={onOpenChange}>
      <DialogContent title={t("deleteAccount")} description={t("accountHint")}>
        <form onSubmit={submit} className="space-y-3" aria-label={t("deleteAccount")} data-testid="onboarding-delete-form">
          {problem && <Alert>{messages[problem] ?? t("failed")}</Alert>}
          <Input label={t("email")} name="email" type="email" required autoComplete="email" />
          {hasPassword && <Input label={t("password")} name="password" type="password" required autoComplete="current-password" />}
          <Button type="submit" variant="danger" loading={busy}>
            {t("deleteAccount")}
          </Button>
        </form>
      </DialogContent>
    </DialogRoot>
  );
}
